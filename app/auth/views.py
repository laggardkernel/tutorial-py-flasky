# -*- coding: utf-8 -*-
# Created by laggard on 10/18/17

from flask import render_template

from . import auth


@auth.route('/login')
def login():
    return render_template('auth/login.html')
