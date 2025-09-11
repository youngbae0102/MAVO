from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

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

def init_db(app):
    """데이터베이스 초기화 및 테스트 데이터 생성"""
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