# -*- coding: utf-8 -*-
# Created by laggard on 10/18/17

from flask import Blueprint

auth = Blueprint('auth', __name__)

# import route views for auth
from . import views
