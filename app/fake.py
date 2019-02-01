#!/usr/bin/env python3
# vim: fileencoding=utf-8 fdm=indent sw=4 ts=4 sts=4
from random import randint
from sqlalchemy.exc import IntegrityError
from faker import Faker
from . import db
from .models import User, Post, Comment


def user(count=100):
    fake = Faker()
    i = 0
    while i < count:
        u = User(
            email=fake.email(),
            username=fake.user_name(),
            password="password",
            confirm=True,
            name=fake.name(),
            location=fake.city(),
            about_me=fake.text(),
            member_since=fake.past_date(),
        )
        db.session.add(u)
        # use try...except cause user must be unique
        try:
            db.session.commit()
            # increase count number only if commit succeeds
            i += 1
        except IntegrityError:
            db.session.rollback()


def post(count=100):
    fake = Faker()
    user_count = User.query.count()
    for i in range(count):
        u = User.query.offset(randint(0, user_count - 1)).first()
        p = Post(body=fake.text(), timestamp=fake.past_date(), author=u)
        db.session.add(u)
    db.session.commit()


def comment(post=None, count=200):
    fake = Faker()
    user_count = User.query.count()
    post_count = Post.query.count()
    if not (user_count and post_count):
        print("No available user or post. Generate thme first.")
    else:
        if post is not None and post in Post.query.all():
            for i in range(count):
                u = User.query.offset(randint(0, user_count) - 1).first()
                c = Comment(
                    body=fake.text(), timestamp=fake.past_data(), author=u, post=post
                )
                db.session.add(c)
            db.session.commit()
        else:
            for i in range(count):
                u = User.query.offset(randint(0, user_count) - 1).first()
                p = Post.query.offset(randint(0, post_count) - 1).first()
                c = Comment(
                    body=fake.text(), timestamp=fake.past_date(), author=u, post=p
                )
                db.session.add(c)
            db.session.commit()
