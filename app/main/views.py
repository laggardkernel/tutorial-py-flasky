# -*- coding: utf-8 -*-

import hashlib
from flask import (
    render_template,
    flash,
    redirect,
    url_for,
    request,
    current_app,
    abort,
    make_response,
)
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries

from . import main  # the blueprint
from .. import db
from ..models import User, Role, Permission, Post, Comment
from .forms import EditProfileForm, EditProfileAdminForm, PostForm, CommentForm
from ..decorators import permission_required, admin_required

# TODO: define hook func conditionally
@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config["FLASKY_SLOW_DB_QUERY_TIME"]:
            current_app.logger.warning(
                "Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n"
                % (query.statement, query.parameters, query.duration, query.context)
            )
    return response


@main.route("/shutdown")
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get("werkzeug.server.shutdown")
    if not shutdown:
        abort(500)
    shutdown()
    return "Shutting down..."


@main.route("/", methods=["GET", "POST"])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE) and form.validate_on_submit():
        post = Post(body=form.body.data, author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        return redirect(url_for("main.index"))
    page = request.args.get("page", 1, type=int)  # page num from query param
    show_followed = False
    if current_user.is_authenticated:
        # show_followed control flag is stored in cookies
        show_followed = bool(request.cookies.get("show_followed", ""))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_POSTS_PER_PAGE"], error_out=False
    )
    posts = pagination.items
    return render_template(
        "index.html",
        form=form,
        posts=posts,
        show_followed=show_followed,
        endpoint="main.index",
        pagination=pagination,
    )


@main.route("/user/<username>")
def user(username):
    """user profile page"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get("page", 1, type=int)  # page num from query param
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_POSTS_PER_PAGE"], error_out=False
    )
    posts = pagination.items
    return render_template(
        "user.html", user=user, posts=posts, pagination=pagination, endpoint="main.user"
    )


@main.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user._get_current_object())
        db.session.commit()
        flash("Your profile has been updated.")
        return redirect(url_for("main.user", username=current_user.username))
    # load existing|old profile
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template("edit_profile.html", form=form)


@main.route("/edit-profile/<int:id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data.lower()
        # avatar_hash is updated automatically by db event listener
        user.username = form.username.data
        if form.password.data:
            user.password = form.password.data
        user.confirmed = form.confirmed.data
        # Note: overwrite user.role but not user.role_id(just a foreign key)
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash("The profile has been updated.")
        return redirect(url_for("main.user", username=user.username))
    # loading existing fields data of the user
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template("edit_profile.html", form=form)


@main.route("/post/<int:id>", methods=["GET", "POST"])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(
            body=form.body.data, post=post, author=current_user._get_current_object()
        )
        db.session.add(comment)
        db.session.commit()
        flash("Your comment has been published.")
        # redirect the last comment page of the current post
        return redirect(url_for("main.post", id=post.id, page=-1))
    page = request.args.get("page", 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // current_app.config[
            "FLASKY_COMMENTS_PER_PAGE"
        ] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"], error_out=False
    )
    comments = pagination.items
    # posts param as a list since the need of template _posts.html
    return render_template(
        "post.html",
        posts=[post],
        form=form,
        comments=comments,
        pagination=pagination,
        endpoint="main.post",
    )


@main.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        db.session.commit()
        flash("The post has been updated.")
        return redirect(url_for("main.post", id=post.id))
    form.body.data = post.body
    return render_template("edit_post.html", form=form)


@main.route("/follow/<username>")
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user!")
        return redirect(url_for("main.index"))
    elif current_user.is_following(user):
        flash("You're already following this user.")
        return redirect(url_for("main.user", username=username))
    else:
        current_user.follow(user)
        db.session.commit()
        flash("You are now following %s." % username)
        return redirect(url_for("main.user", username=username))


@main.route("/unfollow/<username>")
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user!")
        return redirect(url_for("main.index"))
    elif not current_user.is_following(user):
        flash("You are not following this user.")
        return redirect(url_for("main.user", username=username))
    else:
        current_user.unfollow(user)
        db.session.commit()
        flash("You are not following %s anymore." % username)
        return redirect(url_for("main.user", username=username))


@main.route("/followers/<username>")
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user!")
        return redirect(url_for("main.index"))
    else:
        page = request.args.get("page", 1, type=int)
        pagination = user.followers.paginate(
            page,
            per_page=current_app.config["FLASKY_FOLLOWERS_PER_PAGE"],
            error_out=False,
        )  # list of  Follow instances
        follows = [
            {"user": item.follower, "timestamp": item.timestamp}
            for item in pagination.items
        ]
        return render_template(
            "followers.html",
            user=user,
            title="Followers of",
            endpoint="main.followers",
            pagination=pagination,
            follows=follows,
        )


@main.route("/followed-by/<username>")
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user!")
        return redirect(url_for("main.index"))
    else:
        page = request.args.get("page", 1, type=int)
        pagination = user.followed.paginate(
            page,
            per_page=current_app.config["FLASKY_FOLLOWERS_PER_PAGE"],
            error_out=False,
        )
        follows = [
            {"user": item.followed, "timestamp": item.timestamp}
            for item in pagination.items
        ]
        return render_template(
            "followers.html",
            user=user,
            title="Followed by",
            endpoint="main.followed_by",
            pagination=pagination,
            follows=follows,
        )


# set show_followed control flag cookie
@main.route("/all")
# @login_required, available to anonymous as well
def show_all():
    """set show all posts flag before jump to index page"""
    resp = make_response(redirect(url_for("main.index")))
    resp.set_cookie("show_followed", "", max_age=30 * 24 * 60 * 60)
    return resp


@main.route("/followed")
@login_required
def show_followed():
    """set show followed posts flag before jump to index page"""
    resp = make_response(redirect(url_for("main.index")))
    resp.set_cookie("show_followed", "1", max_age=30 * 24 * 60 * 60)
    return resp


@main.route("/moderate")
@login_required
@permission_required(Permission.MODERATE)
def moderate():
    page = request.args.get("page", 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config["FLASKY_COMMENTS_PER_PAGE"], error_out=False
    )
    comments = pagination.items
    return render_template(
        "moderate.html",
        comments=comments,
        pagination=pagination,
        endpoint="main.moderate",
        page=page,
    )


@main.route("/moderate/<int:id>")
@login_required
@permission_required(Permission.MODERATE)
def moderate_flip(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = not comment.disabled
    db.session.add(comment)
    db.session.commit()
    page = request.args.get("page", 1, type=int)
    return redirect(url_for(".moderate", page=page))
