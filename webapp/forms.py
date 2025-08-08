from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, PasswordField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")


class UploadSubmissionForm(FlaskForm):
    file = FileField(
        "Submission File",
        validators=[
            FileRequired(),
            FileAllowed(
                ["pdf", "docx", "doc", "jpg", "jpeg", "png", "tiff", "bmp", "gif"],
                "Unsupported file format",
            ),
        ],
    )
    upload_mode = RadioField(
        "Upload Mode",
        choices=[("single", "Single File"), ("multiple", "Multiple Files")],
        default="single",
        validators=[DataRequired()],
    )
    submit = SubmitField("Upload Files")
