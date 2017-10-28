# -*- coding: utf-8 -*-
# Created by laggard on 10/25/17

from flask import Blueprint

api = Blueprint('api', __name__)

from . import authentication, errors, comments, posts, users
