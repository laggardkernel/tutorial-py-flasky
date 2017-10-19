# -*- coding: utf-8 -*-

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from . import db, login_manager  # app/__init__.py


# ORM models
class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    # backref adds role property into User class
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    """inherit UserMixin class for login detection method"""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    # email as login username
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    @property
    def password(self):
        """use @property decorator to password func as a prop of Role class"""
        raise AttributeError('password is not a readable attribute!')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username


@login_manager.user_loader
def load_user(user_id):
    """load user into current_user?"""
    return User.query.get(int(user_id))
