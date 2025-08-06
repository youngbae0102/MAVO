from flask import Flask, render_template_string
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# DB 연결 설정
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# 모델 정의
class Music(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    filename = db.Column(db.String(100), nullable=False)

@app.before_first_request
def create_tables():
    db.create_all()
    # 최초 실행 시 DB에 샘플 곡 1개 등록
    if not Music.query.first():
        sample = Music(title="Sample Song", filename="sample.mp3")
        db.session.add(sample)
        db.session.commit()

@app.route('/')
def index():
    songs = Music.query.all()
    return render_template_string('''
    <h1>Flask Music Stream (PostgreSQL)</h1>
    {% for song in songs %}
      <p>{{ song.title }}</p>
      <audio controls>
        <source src="/music/{{ song.filename }}" type="audio/mpeg">
      </audio>
    {% endfor %}
    ''', songs=songs)

@app.route('/music/<filename>')
def stream_music(filename):
    return send_from_directory('music', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

