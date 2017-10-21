# -*- coding: utf-8 -*-

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, BooleanField, \
    SelectField, PasswordField
from wtforms.validators import DataRequired, Length, Email, Regexp, \
    ValidationError, EqualTo
from ..models import User, Role


# Form class for username input
class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    submit = SubmitField('Submit')


class EditProfileForm(FlaskForm):
    """update current_user's profile: name, location and about_me"""
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')


class EditProfileAdminForm(FlaskForm):
    """update user's all info fileds by admins"""
    email = StringField('Email',
        validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField(
        'Username', validators=[
            DataRequired(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                'Usernames must have only letters, numbers, dots or underscores')])
    # TODO: change user's password by admin
    password = PasswordField('New Password (leave empty to be untouched)',
        validators=[EqualTo('password2', message='Passwords must match!')])
    password2 = PasswordField('Confirm password')
    confirmed = BooleanField('Confirmed')
    # select list, coerce transform query results(string) into int value
    role = SelectField('Role', coerce=int)  # role_id value
    name = StringField('Real name', validators=[Length(0, 64)])
    location = StringField('Location', validators=[Length(0, 64)])
    about_me = TextAreaField('About me')
    submit = SubmitField('Submit')

    def __init__(self, user, *args, **kwargs):
        super(EditProfileAdminForm, self).__init__(*args, **kwargs)
        # SelectField list for role field in the form:
        # role.id: select value, role.name: display choice for dropdown list
        self.role.choices = [(role.id, role.name) for role in
            Role.query.order_by(Role.name).all()]
        self.user = user

    # custom validators: validate_+field_name
    def validate_email(self, field):
        if field.data != self.user.email and \
                User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered!')

    def validate_username(self, field):
        if field.data != self.user.username and \
                User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use!')
