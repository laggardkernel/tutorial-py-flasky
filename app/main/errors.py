# -*- coding: utf-8 -*-

from flask import render_template, request, jsonify
from . import main


# use main as the global scope not the app
# and app_errorhandler not errorhandler for global error page
@main.app_errorhandler(403)
def forbidden(e):
    if 'application/json' in request.accept_mimetypes \
            and 'text/html' not in request.accept_mimetypes:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('403.html'), 403


@main.app_errorhandler(404)
def page_not_found(e):
    """error handler with content negotiation"""
    if 'application/json' in request.accept_mimetypes \
            and 'text/html' not in request.accept_mimetypes:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('404.html'), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    if 'application/json' in request.accept_mimetypes \
            and 'text/html' not in request.accept_mimetypes:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('500.html'), 500
