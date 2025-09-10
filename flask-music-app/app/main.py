from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Flask-Login 설정
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '로그인이 필요합니다.'

# DB 연결 설정 (외부 PostgreSQL 서버)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.environ.get('DB_USER', 'musicuser')}:{os.environ.get('DB_PASSWORD', 'musicpass')}@{os.environ.get('DB_HOST', '10.10.8.103')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'musicdb')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 사용자 모델
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    # 사용자가 업로드한 음악들과의 관계
    musics = db.relationship('Music', backref='uploader', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 음악 모델
class Music(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    original_filename = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer)
    upload_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Music {self.title}>'

# 폼 정의
class LoginForm(FlaskForm):
    username = StringField('사용자명', validators=[DataRequired()])
    password = PasswordField('비밀번호', validators=[DataRequired()])
    submit = SubmitField('로그인')

class RegisterForm(FlaskForm):
    username = StringField('사용자명', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('이메일', validators=[DataRequired(), Email()])
    password = PasswordField('비밀번호', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('비밀번호 확인', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('회원가입')

class UploadForm(FlaskForm):
    title = StringField('곡 제목', validators=[DataRequired()])
    music_file = FileField('음악 파일', validators=[DataRequired()])
    submit = SubmitField('업로드')

# 허용된 파일 확장자
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'm4a', 'ogg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_upload_folder():
    upload_folder = '/app/music'  # 절대 경로로 변경 (NFS 마운트 포인트)
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

def create_tables():
    with app.app_context():
        db.create_all()
        # 최초 실행 시 테스트 데이터 생성
        if not User.query.first():
            # 기본 사용자 생성
            test_user = User(
                username="testuser",
                email="test@example.com"
            )
            test_user.set_password("password123")
            db.session.add(test_user)
            db.session.commit()
            
            # 샘플 음악 생성 (사용자 ID 포함)
            sample = Music(
                title="Sample Song", 
                filename="sample.mp3",
                original_filename="sample.mp3",
                file_size=0,
                user_id=test_user.id
            )
            db.session.add(sample)
            db.session.commit()

# 인증 라우트
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'어서오세요, {user.username}님!')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('사용자명 또는 비밀번호가 잘못되었습니다.')
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>로그인 - Flask Music Stream</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 40px; background: #f5f5f5; }
            .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; color: #555; }
            input[type="text"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .btn { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #0056b3; }
            .links { text-align: center; margin-top: 20px; }
            .links a { color: #007bff; text-decoration: none; }
            .alert { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .alert-success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .alert-danger { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 로그인</h1>
            
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="alert alert-danger">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                {{ form.hidden_tag() }}
                <div class="form-group">
                    {{ form.username.label }}
                    {{ form.username(class="form-control") }}
                </div>
                <div class="form-group">
                    {{ form.password.label }}
                    {{ form.password(class="form-control") }}
                </div>
                <div class="form-group">
                    {{ form.submit(class="btn") }}
                </div>
            </form>
            
            <div class="links">
                <p>계정이 없으시나요? <a href="{{ url_for('register') }}"> 회원가입</a></p>
                <p><a href="{{ url_for('index') }}"> 메인으로 돌아가기</a></p>
            </div>
        </div>
    </body>
    </html>
    ''', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # 사용자명, 이메일 중복 검사
        if User.query.filter_by(username=form.username.data).first():
            flash('이미 사용 중인 사용자명입니다.')
            return render_template_string(register_template, form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('이미 등록된 이메일입니다.')
            return render_template_string(register_template, form=form)
        
        # 새 사용자 생성
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('login'))
    
    register_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>회원가입 - Flask Music Stream</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 40px; background: #f5f5f5; }
            .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .form-group { margin-bottom: 20px; }
            label { display: block; margin-bottom: 5px; color: #555; }
            input[type="text"], input[type="email"], input[type="password"] { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
            .btn { width: 100%; padding: 12px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            .btn:hover { background: #218838; }
            .links { text-align: center; margin-top: 20px; }
            .links a { color: #007bff; text-decoration: none; }
            .alert { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .alert-danger { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 회원가입</h1>
            
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="alert alert-danger">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                {{ form.hidden_tag() }}
                <div class="form-group">
                    {{ form.username.label }}
                    {{ form.username(class="form-control") }}
                </div>
                <div class="form-group">
                    {{ form.email.label }}
                    {{ form.email(class="form-control") }}
                </div>
                <div class="form-group">
                    {{ form.password.label }}
                    {{ form.password(class="form-control") }}
                </div>
                <div class="form-group">
                    {{ form.password2.label }}
                    {{ form.password2(class="form-control") }}
                </div>
                <div class="form-group">
                    {{ form.submit(class="btn") }}
                </div>
            </form>
            
            <div class="links">
                <p>이미 계정이 있으시나요? <a href="{{ url_for('login') }}"> 로그인</a></p>
                <p><a href="{{ url_for('index') }}"> 메인으로 돌아가기</a></p>
            </div>
        </div>
    </body>
    </html>
    '''
    return render_template_string(register_template, form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.')
    return redirect(url_for('index'))

@app.route('/')
def index():
    search = request.args.get('search', '')
    if search:
        songs = Music.query.filter(Music.title.ilike(f'%{search}%')).all()
    else:
        songs = Music.query.order_by(Music.upload_date.desc()).all()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flask Music Stream</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .upload-form { background: #f9f9f9; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
            .search-form { margin-bottom: 20px; }
            .music-item { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; background: white; }
            .music-title { font-weight: bold; font-size: 18px; color: #333; margin-bottom: 10px; }
            .music-info { color: #666; font-size: 12px; margin-bottom: 10px; }
            audio { width: 100%; margin: 10px 0; }
            .btn { padding: 8px 16px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }
            .btn-danger { background: #dc3545; color: white; }
            .btn-primary { background: #007bff; color: white; }
            input[type="text"], input[type="file"] { padding: 8px; margin: 5px; border: 1px solid #ddd; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 Flask Music Stream 🎵</h1>
            
            <!-- 사용자 정보 -->
            <div style="text-align: right; margin-bottom: 20px; padding: 10px; background: #e9ecef; border-radius: 5px;">
                {% if current_user.is_authenticated %}
                    <span>안녕하세요, <strong>{{ current_user.username }}</strong>님!</span>
                    <a href="{{ url_for('logout') }}" class="btn" style="background: #dc3545; margin-left: 10px;">로그아웃</a>
                {% else %}
                    <a href="{{ url_for('login') }}" class="btn" style="background: #007bff;">로그인</a>
                    <a href="{{ url_for('register') }}" class="btn" style="background: #28a745; margin-left: 10px;">회원가입</a>
                {% endif %}
            </div>
            
            <!-- 업로드 폼 -->
            {% if current_user.is_authenticated %}
            <div class="upload-form">
                <h3>새 음악 업로드</h3>
                <form method="POST" action="/upload" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="곡 제목" required>
                    <input type="file" name="music_file" accept=".mp3,.wav,.flac,.m4a,.ogg" required>
                    <button type="submit" class="btn btn-primary">업로드</button>
                </form>
            </div>
            {% else %}
            <div class="upload-form" style="text-align: center;">
                <h3>음악 업로드</h3>
                <p>음악을 업로드하려면 로그인이 필요합니다.</p>
                <a href="{{ url_for('login') }}" class="btn btn-primary">로그인</a>
                <a href="{{ url_for('register') }}" class="btn" style="background: #28a745; margin-left: 10px;">회원가입</a>
            </div>
            {% endif %}
            
            <!-- 검색 폼 -->
            <div class="search-form">
                <form method="GET">
                    <input type="text" name="search" placeholder="음악 검색..." value="{{ search }}">
                    <button type="submit" class="btn btn-primary">검색</button>
                    <a href="/" class="btn">전체보기</a>
                </form>
            </div>
            
            <!-- 플래시 메시지 -->
            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div style="padding: 10px; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 5px; margin: 10px 0;">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <!-- 음악 목록 -->
            <h3>음악 목록 ({{ songs|length }}곡)</h3>
            {% if songs %}
                {% for song in songs %}
                    <div class="music-item">
                        <div class="music-title">{{ song.title }}</div>
                        <div class="music-info">
                            원본 파일명: {{ song.original_filename }} | 
                            크기: {{ "%.1f"|format(song.file_size/1024/1024) if song.file_size else "N/A" }} MB | 
                            업로드: {{ song.upload_date.strftime('%Y-%m-%d %H:%M') if song.upload_date else "N/A" }} |
                            업로더: {{ song.uploader.username if song.uploader else "Unknown" }}
                        </div>
                        <audio controls preload="none">
                            <source src="/music/{{ song.filename }}" type="audio/mpeg">
                            브라우저가 오디오를 지원하지 않습니다.
                        </audio>
                        {% if current_user.is_authenticated and current_user.id == song.user_id %}
                        <form method="POST" action="/delete/{{ song.id }}" style="display: inline;" onsubmit="return confirm('정말 삭제하시겠습니까?')">
                            <button type="submit" class="btn btn-danger">삭제</button>
                        </form>
                        {% endif %}
                    </div>
                {% endfor %}
            {% else %}
                <p>업로드된 음악이 없습니다.</p>
            {% endif %}
        </div>
    </body>
    </html>
    ''', songs=songs, search=search)

@app.route('/upload', methods=['POST'])
@login_required
def upload_music():
    try:
        title = request.form.get('title')
        music_file = request.files.get('music_file')
        
        if not title or not music_file:
            flash('제목과 파일을 모두 입력해주세요.')
            return redirect(url_for('index'))
        
        if not allowed_file(music_file.filename):
            flash('지원하지 않는 파일 형식입니다. (mp3, wav, flac, m4a, ogg만 가능)')
            return redirect(url_for('index'))
        
        # 파일명 보안 처리
        original_filename = secure_filename(music_file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # 파일 저장
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, unique_filename)
        music_file.save(file_path)
        
        # DB에 저장
        file_size = os.path.getsize(file_path)
        new_music = Music(
            title=title,
            filename=unique_filename,
            original_filename=original_filename,
            file_size=file_size,
            user_id=current_user.id
        )
        db.session.add(new_music)
        db.session.commit()
        
        flash(f'음악 "{title}"이 성공적으로 업로드되었습니다!')
        
    except Exception as e:
        flash(f'업로드 중 오류가 발생했습니다: {str(e)}')
        
    return redirect(url_for('index'))

@app.route('/delete/<int:music_id>', methods=['POST'])
@login_required
def delete_music(music_id):
    try:
        music = Music.query.get_or_404(music_id)
        
        # 사용자가 업로드한 음악인지 확인
        if music.user_id != current_user.id:
            flash('자신이 업로드한 음악만 삭제할 수 있습니다.')
            return redirect(url_for('index'))
        
        # 파일 삭제
        upload_folder = get_upload_folder()
        file_path = os.path.join(upload_folder, music.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # DB에서 삭제
        db.session.delete(music)
        db.session.commit()
        
        flash(f'음악 "{music.title}"이 삭제되었습니다.')
        
    except Exception as e:
        flash(f'삭제 중 오류가 발생했습니다: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/music/<filename>')
def stream_music(filename):
    upload_folder = get_upload_folder()
    return send_from_directory(upload_folder, filename)

@app.route('/api/music')
def api_music_list():
    songs = Music.query.all()
    return jsonify([
        {
            'id': song.id,
            'title': song.title,
            'filename': song.filename,
            'original_filename': song.original_filename,
            'file_size': song.file_size,
            'upload_date': song.upload_date.isoformat() if song.upload_date else None
        } for song in songs
    ])

if __name__ == '__main__':
    create_tables()
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_ENV') == 'development')

