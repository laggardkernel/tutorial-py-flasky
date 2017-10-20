# -*- coding: utf-8 -*-

from flask import Blueprint

# name the Blueprint as 'main'
main = Blueprint('main', __name__)

# import at the end in case of loop dependence
from . import views, errors
from ..models import Permission


@main.app_context_processor
def inject_permissions():
    """inject Permission class into app_context for use in template"""
    return dict(Permission=Permission)
