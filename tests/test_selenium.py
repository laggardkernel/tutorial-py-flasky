# -*- coding: utf-8 -*-

import re
import threading
import time
import unittest
from selenium import webdriver
from app import create_app, db
from app.models import Role, User, Post


class SeleniumTestCase(unittest.TestCase):
    client = None

    @classmethod
    def setUpClass(cls):
        # launcher browser
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        try:
            cls.client = webdriver.Chrome(chrome_options=options)
        except:
            pass

        # jump these tests if browser not launched
        if cls.client:
            # create app
            cls.app = create_app("testing")
            cls.app_context = cls.app.app_context()
            cls.app_context.push()

            # forbid log, keep output simple
            import logging

            logger = logging.getLogger("werkzeug")
            logger.setLevel("ERROR")

            # create db and fill it with dummy data
            db.create_all()
            Role.insert_roles()
            User.generate_fake(10)
            Post.generate_fake(10)

            # add an admin
            admin_role = Role.query.filter_by(name="Administrator").first()
            admin = User(
                email="john@example.com",
                username="john",
                password="cat",
                role=admin_role,
                confirmed=True,
            )
            db.session.add(admin)
            db.session.commit()

            # start Flask server in a thread
            cls.server_thread = threading.Thread(target=cls.app.run)
            cls.server_thread.start()
            # give the server 1s to ensure it's up
            time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        if cls.client:
            # stop browser and the flask server
            cls.client.get("http://localhost:5000/shutdown")
            cls.client.quit()
            cls.server_thread.join()

            # destroy database
            db.drop_all()
            db.session.remove()

            # remove app context
            cls.app_context.pop()

    def setUp(self):
        if not self.client:
            self.skipTest("Web browser not available")

    def tearDown(self):
        pass

    def test_admin_home_page(self):
        # navigate to index page
        self.client.get("http://localhost:5000/")
        self.assertTrue(re.search("Hello,\s+Stranger\s*!", self.client.page_source))

        # navigate to login page
        self.client.find_element_by_link_text("Log In").click()
        self.assertTrue("<h1>Log In</h1>" in self.client.page_source)

        # login
        self.client.find_element_by_name("email").send_keys("john@example.com")
        self.client.find_element_by_name("password").send_keys("cat")
        self.client.find_element_by_name("submit").click()
        self.assertTrue(re.search("Hello,\s+john\s*!", self.client.page_source))

        # navigate to profile page of oneself
        self.client.find_element_by_link_text("Profile").click()
        self.assertTrue("<h1>john</h1>" in self.client.page_source)
