# -*- coding: utf-8 -*-

from datetime import datetime
import hashlib
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app, request, url_for
from markdown import markdown
import bleach
from . import db, login_manager  # app/__init__.py
from .exceptions import ValidationError


class Permission:
    FOLLOW = 0x01
    COMMENT = 0x02
    WRITE = 0x04
    MODERATE = 0x08
    ADMIN = 0x80  # 128


# ORM models
class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    # default role for all created users
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)

    # backref adds role property into User class
    users = db.relationship("User", backref="role", lazy="dynamic")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        """Add role instances into roles table of database"""
        roles = {
            "User": (Permission.FOLLOW | Permission.COMMENT | Permission.WRITE,),
            "Moderator": (
                Permission.FOLLOW
                | Permission.COMMENT
                | Permission.WRITE
                | Permission.MODERATE,
            ),
            # all permissions include future ones for admin
            "Administrator": (0xFF,),
        }
        default_role = "User"
        for r in roles.keys():
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.permissions = roles[r][0]
            role.default = role.name == default_role
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permission(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return "<Role %r>" % self.name


class Follow(db.Model):
    __tablename__ = "follows"
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class User(UserMixin, db.Model):
    """inherit UserMixin class for login detection method"""

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    # email as login username
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"))

    # user profile info
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)

    avatar_hash = db.Column(db.String(32))

    posts = db.relationship("Post", backref="author", lazy="dynamic")

    # self reference, return Follow instance
    followed = db.relationship(
        "Follow",
        foreign_keys=[Follow.follower_id],
        backref=db.backref("follower", lazy="joined"),
        lazy="dynamic",
        cascade="all,delete-orphan",
    )
    followers = db.relationship(
        "Follow",
        foreign_keys=[Follow.followed_id],
        backref=db.backref("followed", lazy="joined"),
        lazy="dynamic",
        cascade="all,delete-orphan",
    )

    comments = db.relationship("Comment", backref="author", lazy="dynamic")

    @staticmethod
    def generate_fake(count=100):
        """forge some fake users, number of users is count"""
        from sqlalchemy.exc import IntegrityError
        from random import seed
        import forgery_py

        seed()
        for i in range(count):
            u = User(
                email=forgery_py.internet.email_address(),
                username=forgery_py.internet.user_name(True),
                password=forgery_py.lorem_ipsum.word(),
                confirmed=True,
                name=forgery_py.name.full_name(),
                location=forgery_py.address.city(),
                about_me=forgery_py.lorem_ipsum.sentence(),
                member_since=forgery_py.date.date(True),
            )
            db.session.add(u)
            # use try...except... cause user must be unique
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()

    @staticmethod
    def add_self_follows():
        """
        create new func to upgrade db: follow oneself
        Note: watch out the side-effect on count and pagination
        """
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __init__(self, **kw):
        super(User, self).__init__(**kw)
        if self.role is None:
            if self.email == current_app.config["FLASKY_ADMIN"]:
                self.role = Role.query.filter_by(permissions=0xFF).first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode("utf-8")).hexdigest()
        # follow oneself
        self.followed.append(Follow(followed=self))

    @property
    def password(self):
        """use @property decorator to password func as a prop of Role class"""
        raise AttributeError("password is not a readable attribute!")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        """generate token from User.id"""
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"confirm": self.id}).decode("utf-8")

    def confirm(self, token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get("confirm") != self.id:
            return False
        self.confirmed = True
        db.session.add(self)  # update database
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        r = s.dumps({"reset": self.id}).decode("utf-8")
        r = self.email + ":" + r
        r = base64.b64encode(r.encode("utf-8")).decode("utf-8")
        return r

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get("reset") != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"change_email": self.id, "new_email": new_email}).decode("utf-8")

    def change_email(self, token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get("change_email") != self.id:
            return False
        new_email = data.get("new_email")
        # You'll never be too careful, right? Check the email address again.
        if User.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        db.session.add(self)
        return True

    def can(self, perm):
        """verify user's permissions"""
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        """update last_seen date"""
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default="identicon", rating="g"):
        if request.is_secure:
            url = "https://secure.gravatar.com/avatar"
        else:
            url = "http://www.gravatar.com/avatar"
        hash = self.avatar_hash or hashlib.md5(self.email.encode("utf-8")).hexdigest()
        return "{url}/{hash}?s={size}&d={default}&r={rating}".format(
            url=url, hash=hash, size=size, default=default, rating=rating
        )

    def is_following(self, user):
        return self.followed.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        # Specific followed_id is needed to undo the relationship
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)  # delete the Follow instance

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(
            Follow.follower_id == self.id
        )

    def generate_auth_token(self, expiration):
        """temp auth token to avoid sensitive password auth at each request"""
        s = Serializer(current_app.config["SECRET_KEY"], expires_in=expiration)
        return s.dumps({"id": self.id}).decode("utf-8")

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get_or_404(data["id"])

    @staticmethod
    def on_changed_email(target, value, oldvalue, initiator):
        """Update avatar_hash once email is changed"""
        target.avatar_hash = hashlib.md5(value.encode("utf-8")).hexdigest()

    def to_json(self):
        json_user = {
            "url": url_for("api.get_user", id=self.id, _external=True),
            "username": self.username,
            "name": self.name,
            "location": self.location,
            "about_me": self.about_me,
            "member_since": self.member_since,
            "last_seen": self.last_seen,
            "posts": url_for("api.get_user_posts", id=self.id, _external=True),
            "followed_posts": url_for(
                "api.get_user_followed_posts", id=self.id, _external=True
            ),
            "post_count": self.posts.count(),
        }
        return json_user

    def __repr__(self):
        return "<User %r>" % self.username


db.event.listen(User.email, "set", User.on_changed_email)


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


# Model class for anonymous_user from Flask-Login
login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    """load user into current_user?"""
    return User.query.get(int(user_id))


class Post(db.Model):
    __tablename__ = "posts"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)  # auto generated from Post.body
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    comments = db.relationship("Comment", backref="post", lazy="dynamic")

    @staticmethod
    def generate_fake(count=100):
        """random forge fake posts for random users"""
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        for i in range(count):
            # random select a user and forge a fake post
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(
                body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                timestamp=forgery_py.date.date(True),
                author=u,
            )
            db.session.add(p)
            db.session.commit()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """transform markdown text into html text and save it"""
        allowed_tags = [
            "a",
            "abbr",
            "acronym",
            "b",
            "blockquote",
            "code",
            "em",
            "i",
            "li",
            "ol",
            "pre",
            "strong",
            "ul",
            "h1",
            "h2",
            "h3",
            "p",
        ]
        # linkify during markdown trans, which is not supported by the later
        target.body_html = bleach.linkify(
            bleach.clean(
                markdown(value, output_format="html"), tags=allowed_tags, strip=True
            )
        )

    def to_json(self):
        json_post = {
            "url": url_for("api.get_post", id=self.id, _external=True),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author": url_for("api.get_user", id=self.author_id, _external=True),
            "comments": url_for("api.get_post_comments", id=self.id, _external=True),
            "comment_count": self.comments.count(),
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get("body")
        if body is None or body == "":
            raise ValidationError("post does not have a body")
        # the client has no permission to choose author of a post
        # author will be appointed in route from api
        return Post(body=body)


# execute Post.on_change_body() func once new value is set for Post.body
db.event.listen(Post.body, "set", Post.on_changed_body)


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"))

    @staticmethod
    def generate_fake(post="", count=200):
        from random import seed, randint
        import forgery_py

        seed()
        user_count = User.query.count()
        post_count = Post.query.count()
        if user_count and post_count:
            if post is not None and post in Post.query.all():
                for i in range(count):
                    u = User.query.offset(randint(0, user_count) - 1).first()
                    c = Comment(
                        body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                        timestamp=forgery_py.date.date(True),
                        author=u,
                        post=post,
                    )
                    db.session.add(c)
                    db.session.commit()
            else:
                for i in range(count):
                    u = User.query.offset(randint(0, user_count) - 1).first()
                    p = Post.query.offset(randint(0, post_count) - 1).first()
                    c = Comment(
                        body=forgery_py.lorem_ipsum.sentences(randint(1, 3)),
                        timestamp=forgery_py.date.date(True),
                        author=u,
                        post=p,
                    )
                    db.session.add(c)
                    db.session.commit()
        else:
            print("No available user or post. Generate them first.")

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        """markdown text --> html"""
        allowed_tags = ["a", "abbr", "acronym", "b", "code", "em", "i", "strong"]
        target.body_html = bleach.linkify(
            bleach.clean(
                markdown(value, output_format="html"), tags=allowed_tags, strip=True
            )
        )

    def to_json(self):
        json_comment = {
            "url": url_for("api.get_comment", id=self.id, _external=True),
            "post": url_for("api.get_post", id=self.post_id, _external=True),
            "body": self.body,
            "body_html": self.body_html,
            "timestamp": self.timestamp,
            "author": url_for("api.get_user", id=self.author_id, _external=True),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get("body")
        if body is None or body == "":
            raise ValidationError("comment does not have a body")
        # author will be appointed in route from api later
        return Comment(body=body)


db.event.listen(Comment.body, "set", Comment.on_changed_body)
