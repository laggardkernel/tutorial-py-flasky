# -*- coding: utf-8 -*-

from flask import render_template

from . import main  # the bluepring
from ..models import User


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/user/<username>')
def user(username):
    """user profile page"""
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html', user=user)
