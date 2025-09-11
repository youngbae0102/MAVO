from flask_wtf import FlaskForm
from wtforms import StringField, FileField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email, Length, EqualTo

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