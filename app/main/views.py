# -*- coding: utf-8 -*-

import hashlib
from flask import render_template, flash, redirect, url_for, request, \
    current_app
from flask_login import login_required, current_user

from . import main  # the bluepring
from .. import db
from ..models import User, Role, Permission, Post
from .forms import EditProfileForm, EditProfileAdminForm, PostForm
from ..decorators import admin_required


@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) \
            and form.validate_on_submit():
        post = Post(body=form.body.data,
            author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('main.index'))
    page = request.args.get('page', 1, type=int)  # page num from query param
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('index.html', form=form, posts=posts,
        pagination=pagination)


@main.route('/user/<username>')
def user(username):
    """user profile page"""
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)  # page num from query param
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('user.html', user=user, posts=posts,
        pagination=pagination)


@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('main.user', username=current_user.username))
    # load existing|old profile
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        # don't forget to update avatar_hash once email updated
        user.avatar_hash = hashlib.md5(
            form.email.data.encode('utf-8')).hexdigest()
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
        flash('The profile has been updated.')
        return redirect(url_for('main.user', username=user.username))
    # loading existing fields data of the user
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/post/<int:id>')
def post(id):
    post = Post.query.get_or_404(id)
    # posts param as a list since the need of template _posts.html
    return render_template('post.html', posts=[post])
