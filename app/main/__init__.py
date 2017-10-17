# -*- coding: utf-8 -*-

from flask import Blueprint

# name the Blueprint as 'main'
main = Blueprint('main', __name__)

# import at the end in case of loop dependence
from . import views, errors
