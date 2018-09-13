# -*- coding: utf-8 -*-

from flask import request, current_app, url_for, jsonify
from ..models import Comment
from . import api


@api.route("/comments/")
def get_comments():
    """return all comments"""
    page = request.args.get("page", 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"], error_out=False
    )
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_comments", page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for("api.get_comments", page=page + 1, _external=True)
    return jsonify(
        {
            "comments": [comment.to_json() for comment in comments],
            "prev": prev,
            "next": next,
            "count": pagination.total,
        }
    )


@api.route("/comments/<int:id>")
def get_comment(id):
    comment = Comment.query.get_or_404(id)
    return jsonify(comment.to_json())
