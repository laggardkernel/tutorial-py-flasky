# -*- coding: utf-8 -*-

import base64
from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from . import auth
from .. import db
from ..models import User
from ..email import send_email
from ..main.errors import page_not_found
from .forms import (
    LoginForm,
    RegistrationForm,
    ChangePasswordForm,
    PasswordResetForm,
    PasswordResetRequestForm,
    ChangeEmailRequestForm,
)


# permission filter
@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()  # update last_seen at each request
        if (
            not current_user.confirmed
            and request.endpoint
            and request.endpoint[:5] != "auth."
            and request.endpoint != "static"
        ):
            return redirect(url_for("auth.unconfirmed"))


@auth.route("/unconfirmed")
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for("main.index"))
    return render_template("auth/unconfirmed.html")


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get("next") or url_for("main.index"))
        flash("Invalid username or password!")
    return render_template("auth/login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("main.index"))


@auth.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            email=form.email.data,
            username=form.username.data,
            password=form.password.data,
        )
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(
            user.email,
            "Confirm Your Account",
            "auth/email/confirm",
            user=user,
            token=token,
        )
        flash("A confirmation email has been sent to you.")
        return redirect(url_for("main.index"))
    return render_template("auth/register.html", form=form)


@auth.route("/confirm/<token>")
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for("main.index"))
    elif current_user.confirm(token):
        flash("You have confirmed your account. Thanks!")
    else:
        flash("The confirmation link is invalid or has expired!")
    return redirect(url_for("main.index"))


@auth.route("/confirm")
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(
        current_user.email,
        "Confirm Your Account",
        "auth/email/confirm",
        user=current_user,
        token=token,
    )
    flash("A new confirmation email has been sent to you.")
    return redirect(url_for("main.index"))


@auth.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            flash("Your password has been updated.")
            return redirect(url_for("main.index"))
        else:
            flash("Invalid password.")
    return render_template("auth/change_password.html", form=form)


@auth.route("/reset", methods=["GET", "POST"])
def password_reset_request():
    """Send password reset link to user's email address"""
    if not current_user.is_anonymous:
        flash("Reset password is for user who forgot the password.")
        return redirect(url_for("main.index"))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():  # send email to user to reset password
        user = User.query.filter_by(email=form.email.data.lower()).first()
        # check email existence in view but not in form to save db query once
        if user:
            token = user.generate_reset_token()
            send_email(
                user.email,
                "Reset Your Password",
                "auth/email/reset_password",
                user=user,
                token=token,
            )
            flash(
                "An email with instructions to reset your password has been sent to you."
            )
            return redirect(url_for("auth.login"))
        else:
            flash("Invalid email address!")
    return render_template("auth/reset_password.html", form=form)


# DONE: set email field uneditible and fill it with reset email from token
@auth.route("/reset/<token>", methods=["GET", "POST"])
def password_reset(token):
    if not current_user.is_anonymous:
        flash("Logout first before resetting your password.")
        return redirect(url_for("main.index"))

    try:
        email, token = base64.b64decode(token).decode("utf-8").split(":")
    except:
        # TODO: use err msg in err handler
        return page_not_found(e="invalid token")

    form = PasswordResetForm()
    form.email.data = email
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        # validate email existence to save one time db query
        if user and user.reset_password(token, form.password.data):
            db.session.commit()
            flash("Your password has been updated.")
            return redirect(url_for("auth.login"))
        else:
            flash("The reset link is invalid or has expired!")
            return redirect(url_for("main.index"))
    return render_template("auth/reset_password.html", form=form)


@auth.route("/change-email", methods=["GET", "POST"])
@login_required
def change_email_request():
    """Send email confirmation link to user's new email address"""
    form = ChangeEmailRequestForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data
            token = current_user.generate_email_change_token(new_email)
            send_email(
                new_email,
                "Confirm Your New Email Address",
                "auth/email/change_email",
                user=current_user,
                token=token,
            )
            flash(
                "An email with instructions to confirm your new email address "
                "has been sent to you."
            )
            return redirect(url_for("main.index"))
        else:
            flash("Invalid password!")
    return render_template("auth/change_email.html", form=form)


@auth.route("/change-email/<token>")
@login_required
def change_email(token):
    if current_user.change_email(token):
        flash("You email address has been updated.")
    else:
        flash("Invalid request!")
    return redirect(url_for("main.index"))
