# -*- coding: utf-8 -*-

from functools import wraps
from flask import abort
from flask_login import current_user
from .models import Permission


def permission_required(permission):
    """decorator for permission requirement"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kw):
            if not current_user.can(permission):
                abort(403)  # Forbidden
            else:
                return f(*args, **kw)

        return decorated_function

    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)
