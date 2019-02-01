#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import click

COV = None
if os.environ.get("FLASK_COVERAGE"):
    import coverage

    COV = coverage.coverage(branch=True, include="app/*")
    COV.start()

from app import create_app, db
from app.models import User, Follow, Role, Permission, Post, Comment
from flask_migrate import Migrate, MigrateCommand

app = create_app(os.getenv("FLASK_CONFIG") or "default")
# init Migrate, and the db subcommand is integrated into flask automatically
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    """shell context to auto import modules in shell environ"""
    return dict(
        app=app,
        db=db,
        User=User,
        Follow=Follow,
        Role=Role,
        Permission=Permission,
        Post=Post,
        Comment=Comment,
    )


@app.cli.command()
@click.argument("test_names", nargs=-1)
def test(test_names="", coverage=False):
    """Run the unit tests."""
    if coverage and not os.environ.get("FLASK_COVERAGE"):
        import sys

        os.environ["FLASK_COVERAGE"] = "1"
        os.execvp(sys.executable, [sys.executable] + sys.argv)

    import unittest

    if test_names:
        tests = unittest.Tes().loadTestsFromNames(test_names)
    else:
        # load test methods from the directory tests
        tests = unittest.TestLoader().discover("tests")
    unittest.TextTestRunner(verbosity=2).run(tests)
    if COV:
        import shutil

        COV.stop()
        COV.save()
        print("Coverage Summary:")
        COV.report()
        basedir = os.path.abspath(os.path.dirname(__file__))
        covdir = os.path.join(basedir, "tmp/coverage")
        shutil.rmtree(covdir)
        COV.html_report(directory=covdir)
        print("HTML version: file://%s/index.html" % covdir)
        COV.erase()


@app.cli.command()
@click.option("--length", default=25, help="Profile stack length")
@click.option("--profile-dir", default=None, help="Profile directory")
def profile(length, profile_dir):
    """start the app under the code profiler."""
    from werkzeug.middleware.profiler import ProfilerMiddleware

    app.wsgi_app = ProfilerMiddleware(
        app.wsgi_app, restrictions=[length], profile_dir=profile_dir
    )
    app.run()


@app.cli.command()
def deploy():
    """Run deployment tasks."""
    from flask_migrate import upgrade
    from app.models import Role, User

    # migrate database to the latest version
    upgrade()

    # create user roles
    Role.insert_roles()

    # create self-follows for all users
    User.add_self_follows()
