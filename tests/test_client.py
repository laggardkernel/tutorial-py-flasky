# -*- coding: utf-8 -*-

import unittest
import re
from flask import url_for
from app import create_app, db
from app.models import User, Role


class FlaskClientTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        Role.insert_roles()
        # test_client from Flask
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_home_page(self):
        response = self.client.get(url_for("main.index"))
        self.assertEqual(response.status_code, 200)
        # default response.data|response.get_data() is binary string,
        # use response.get_data(as_text=True) to convert it into unicode string
        self.assertTrue("Stranger" in response.get_data(as_text=True))

    def test_register_and_login(self):
        # register a new account
        response = self.client.post(
            url_for("auth.register"),
            data={
                "email": "john@example.com",
                "username": "john",
                "password": "cat",
                "password2": "cat",
            },
        )
        self.assertTrue(response.status_code == 302)  # redirected to index

        # login with the new account
        response = self.client.post(
            url_for("auth.login"),
            data={"email": "john@example.com", "password": "cat"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_data(as_text=True)
        self.assertTrue(re.search("Hello,\s+john!", data))
        self.assertTrue("You have not confirmed you account yet" in data)

        # send a confirmation token
        user = User.query.filter_by(email="john@example.com").first()
        token = user.generate_confirmation_token()
        response = self.client.get(
            url_for("auth.confirm", token=token), follow_redirects=True
        )
        user.confirm(token)
        db.session.commit()
        self.assertEqual(response.status_code, 200)
        data = response.get_data(as_text=True)
        self.assertTrue("You have confirmed your account" in data)

        # logout
        response = self.client.get(url_for("auth.logout"), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        data = response.get_data(as_text=True)
        self.assertTrue("You have been logged out" in data)
