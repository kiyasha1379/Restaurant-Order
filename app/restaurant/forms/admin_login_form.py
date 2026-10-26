"""The staff sign-in form."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    """E-mail and password. Messages come from the translator in the template."""

    email = StringField(validators=[DataRequired(), Length(max=255)])
    password = PasswordField(validators=[DataRequired(), Length(max=200)])
