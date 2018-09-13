# -*- coding: utf-8 -*-

from flask import g, request, jsonify, url_for, current_app
from . import api
from .decorators import permission_required
from .errors import forbidden
from ..models import Comment, Post, Permission
from .. import db

# TODO: add auth requirement, @auth.login_required
@api.route("/posts/")
def get_posts():
    page = request.args.get("page", 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_POSTS_PER_PAGE"], error_out=False
    )
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_posts", page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for("api.get_posts", page=page + 1, _external=True)
    return jsonify(
        {
            "posts": [post.to_json() for post in posts],
            "prev": prev,
            "next": next,
            "count": pagination.total,
        }
    )


@api.route("/posts/", methods=["POST"])
@permission_required(Permission.WRITE_ARTICLES)
def new_post():
    post = Post.from_json(request.json)
    # Note: g.current_user is not an agent like current_user
    post.author = g.current_user
    db.session.add(post)
    # commit at once manually, to generate fields for .to_json
    db.session.commit()
    # return entity-body, status-code and header in HTTP message
    return (
        jsonify(post.to_json()),
        201,
        {"Location": url_for("api.get_post", id=post.id, _external=True)},
    )


@api.route("/posts/<int:id>")
def get_post(id):
    # 404 error handler should be compatible with json format
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())


# update existing post with PUT, namely store message entity-body on the server
@api.route("/posts/<int:id>", methods=["PUT"])
@permission_required(Permission.WRITE_ARTICLES)
def edit_post(id):
    post = Post.query.get_or_404(id)
    if g.current_user != post.author and not g.current_user.can(Permission.ADMINISTER):
        return forbidden("Insufficient permissions")
    else:
        post.body = request.json.get("body", post.body)
        db.session.add(post)  # body_html will be updated automatically
        return jsonify(post.to_json())


@api.route("/posts/<int:id>/comments/")
def get_post_comments(id):
    post = Post.query.get_or_404(id)
    page = request.args.get("page", 1, type=int)
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"], error_out=False
    )
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for("api.get_post_comments", id=id, page=page - 1, _external=True)
    next = None
    if pagination.has_next:
        next = url_for("api.get_post_comments", id=id, page=page + 1, _external=True)
    return jsonify(
        {
            "comments": [comment.to_json() for comment in comments],
            "prev": prev,
            "next": next,
            "count": pagination.total,
        }
    )


@api.route("/posts/<int:id>/comments/", methods=["POST"])
@permission_required(Permission.COMMENT)
def new_post_comment(id):
    post = Post.query.get_or_404(id)
    comment = Comment.from_json(request.json)
    comment.author = g.current_user
    comment.post = post
    db.session.add(comment)
    db.session.commit()
    return (
        jsonify(comment.to_json()),
        201,
        {"Location": url_for("api.get_comment", id=comment.id, _external=True)},
    )
