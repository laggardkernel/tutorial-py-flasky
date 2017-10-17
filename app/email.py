# -*- coding: utf-8 -*-

from threading import Thread
from flask import render_template, current_app
from flask_mail import Message

from . import mail


def send_async_mail(app, msg):
    with app.app_context():
        mail.send(msg)


def send_mail(to, subject, template, **kw):
    # get the current app object, use current_app as app variable is OK as well.
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' '+ subject,
        sender=app.config['FLASK_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kw)
    msg.html = render_template(template + '.html', **kw)
    thr = Thread(target=send_async_mail, args=[app, msg])
    thr.start()
    return thr
