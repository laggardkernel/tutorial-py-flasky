# -*- coding: utf-8 -*-
# Created by laggard on 10/19/17

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email


# Form for user login page
class LoginForm(FlaskForm):
    email = StringField('Email',
        validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')
