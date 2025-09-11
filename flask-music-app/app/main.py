import os
import uuid
from flask import Blueprint, render_template, send_from_directory, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .models import Music, db
from .config import Config

main = Blueprint('main', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def get_upload_folder():
    upload_folder = Config.UPLOAD_FOLDER
    os.makedirs(upload_folder, exist_ok=True)
    return upload_folder

@main.route('/')
def index():
    search = request.args.get('search', '')
    if search:
        songs = Music.query.filter(Music.title.ilike(f'%{search}%')).all()
    else:
        songs = Music.query.order_by(Music.upload_date.desc()).all()
    
    return render_template('index.html', songs=songs, search=search)

@main.route('/upload', methods=['POST'])
@login_required
def upload_music():
    try:
        title = request.form.get('title')
        music_file = request.files.get('music_file')
        
        if not title or not music_file:
            flash('제목과 파일을 모두 입력해주세요.')
            return redirect(url_for('main.index'))
        
        if not allowed_file(music_file.filename):
            flash('지원하지 않는 파일 형식입니다. (mp3, wav, flac, m4a, ogg만 가능)')
            return redirect(url_for('main.index'))
        
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
        
    return redirect(url_for('main.index'))

@main.route('/delete/<int:music_id>', methods=['POST'])
@login_required
def delete_music(music_id):
    try:
        music = Music.query.get_or_404(music_id)
        
        # 사용자가 업로드한 음악인지 확인
        if music.user_id != current_user.id:
            flash('자신이 업로드한 음악만 삭제할 수 있습니다.')
            return redirect(url_for('main.index'))
        
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
    
    return redirect(url_for('main.index'))

@main.route('/music/<filename>')
def stream_music(filename):
    upload_folder = get_upload_folder()
    return send_from_directory(upload_folder, filename)

@main.route('/api/music')
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