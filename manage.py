#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Created by laggard on 10/17/17

import os
from app import create_app, db
from app.models import User, Role
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    """shell context to auto import modules in shell environ"""
    return dict(app=app, db=db, User=User, Role=Role)


# context imported automatically by shell make_contex
manager.add_command('shell', Shell(make_context=make_shell_context))
# integrate db command into Flask-Script
manager.add_command('db', MigrateCommand)


# custom manager command for manager shell
@manager.command
def test():
    """Run the unit tests."""
    import unittest
    # load test methods from the directory tests
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    manager.run()
