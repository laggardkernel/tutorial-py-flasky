# -*- coding: utf-8 -*-

from flask import Flask
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config

# without parameter, not initialized
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy()


def create_app(config_name):
    """factory func to create and init app instance"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    config[config_name].init_app(app)
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)

    # additional routes and custom error pages.
    # The problem here is app has not be created until this func(create_app) is
    # called. We can't use @app.route() since there is no scope of the app.
    # So we use Blueprint to avoid the problem.
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
