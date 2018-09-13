# -*- coding: utf-8 -*-

from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from ..models import User, AnonymousUser
from ..main.errors import forbidden
from .errors import unauthorized
from . import api

# since only used in api blueprint, namely in /api/version/*
# no need to init in app/__init__.py
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    """save authorized user in app context g"""
    if email_or_token == "":
        g.current_user = AnonymousUser()  # app context during each request
        return True
    elif password == "":
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    else:
        user = User.query.filter_by(email=email_or_token).first()
        if not user:
            return False
        else:
            g.current_user = user
            g.token_used = False
            return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized("Invalid credentials")


@api.before_request
@auth.login_required
def before_request():
    if not g.current_user.is_anonymous and not g.current_user.confirmed:
        return forbidden("Unconfirmed account")


@api.route("/token")
def get_token():
    # to avoid token generation with an old token
    if g.current_user.is_anonymous or g.token_used:
        return unauthorized("Invalid credentials")
    return jsonify(
        {
            "token": g.current_user.generate_auth_token(expiration=3600),
            "expiration": 3600,
        }
    )
