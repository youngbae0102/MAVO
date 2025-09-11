from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from .models import User, db
from .forms import LoginForm, RegisterForm

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f'어서오세요, {user.username}님!')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('사용자명 또는 비밀번호가 잘못되었습니다.')
    
    return render_template('auth/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        # 사용자명, 이메일 중복 검사
        if User.query.filter_by(username=form.username.data).first():
            flash('이미 사용 중인 사용자명입니다.')
            return render_template('auth/register.html', form=form)
        
        if User.query.filter_by(email=form.email.data).first():
            flash('이미 등록된 이메일입니다.')
            return render_template('auth/register.html', form=form)
        
        # 새 사용자 생성
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.')
    return redirect(url_for('main.index'))