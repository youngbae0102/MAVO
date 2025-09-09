from flask import Flask, render_template_string, send_from_directory, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SubmitField
from wtforms.validators import DataRequired
import os
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# DB 연결 설정 (외부 PostgreSQL 서버)
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.environ.get('DB_USER', 'musicuser')}:{os.environ.get('DB_PASSWORD', 'musicpass')}@{os.environ.get('DB_HOST', '10.10.8.103')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'musicdb')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 모델 정의
class Music(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    original_filename = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer)
    upload_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Music {self.title}>'

# 폼 정의
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
        # 최초 실행 시 DB에 샘플 곡 1개 등록
        if not Music.query.first():
            sample = Music(
                title="Sample Song", 
                filename="sample.mp3",
                original_filename="sample.mp3",
                file_size=0
            )
            db.session.add(sample)
            db.session.commit()

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
            
            <!-- 업로드 폼 -->
            <div class="upload-form">
                <h3>새 음악 업로드</h3>
                <form method="POST" action="/upload" enctype="multipart/form-data">
                    <input type="text" name="title" placeholder="곡 제목" required>
                    <input type="file" name="music_file" accept=".mp3,.wav,.flac,.m4a,.ogg" required>
                    <button type="submit" class="btn btn-primary">업로드</button>
                </form>
            </div>
            
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
                            업로드: {{ song.upload_date.strftime('%Y-%m-%d %H:%M') if song.upload_date else "N/A" }}
                        </div>
                        <audio controls preload="none">
                            <source src="/music/{{ song.filename }}" type="audio/mpeg">
                            브라우저가 오디오를 지원하지 않습니다.
                        </audio>
                        <form method="POST" action="/delete/{{ song.id }}" style="display: inline;" onsubmit="return confirm('정말 삭제하시겠습니까?')">
                            <button type="submit" class="btn btn-danger">삭제</button>
                        </form>
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
            file_size=file_size
        )
        db.session.add(new_music)
        db.session.commit()
        
        flash(f'음악 "{title}"이 성공적으로 업로드되었습니다!')
        
    except Exception as e:
        flash(f'업로드 중 오류가 발생했습니다: {str(e)}')
        
    return redirect(url_for('index'))

@app.route('/delete/<int:music_id>', methods=['POST'])
def delete_music(music_id):
    try:
        music = Music.query.get_or_404(music_id)
        
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

