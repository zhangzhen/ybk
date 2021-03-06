#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask, render_template
from flask.ext.login import LoginManager
from flask.ext.assets import Environment

from ybk.frontend import frontend
from ybk.user import user
from ybk.api import api
from ybk.admin import admin
from ybk.models import User


blueprints = [
    frontend,
    user,
    api,
    admin,
]


def create_app(conf={}):
    app = Flask(__name__)
    configure_app(app, conf)
    configure_hook(app)
    configure_blueprints(app, blueprints)
    configure_extensions(app)
    configure_logging(app)
    configure_template_filters(app)
    configure_error_handlers(app)
    return app


def configure_app(app, conf):
    for key, value in conf.items():
        app.config[key] = value


def configure_hook(app):
    @app.before_request
    def before_request():
        pass


def configure_blueprints(app, blueprints):
    """Configure blueprints in views."""
    for blueprint in blueprints:
        app.register_blueprint(blueprint)


def configure_extensions(app):
    # flask-mail
    # flask-cache
    # flask-login
    # flask-openid
    login_manager = LoginManager()

    login_manager.login_view = 'user.login'
    login_manager.refresh_view = 'user.refresh'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query_one({'_id': user_id})

    login_manager.setup_app(app)

    assets = Environment()
    assets.init_app(app)


def configure_logging(app):
    pass


def configure_template_filters(app):
    @app.template_filter()
    def strformat(v, fmt):
        try:
            return fmt.format(v)
        except:
            return v

    @app.template_filter()
    def percentage(f, fmt='4.1'):
        try:
            return ('{:' + fmt + 'f}%').format(float(f) * 100)
        except:
            return f

    @app.template_filter()
    def bjdate(d):
        from datetime import timedelta
        if d:
            return (d + timedelta(hours=8)).strftime('%Y-%m-%d')

    @app.template_filter()
    def bjtime(t):
        from datetime import timedelta
        if t:
            return (t + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')

    @app.template_filter()
    def mask(v):
        v = str(v)
        if len(v) <= 2:
            return v
        else:
            return v[0] + '*' * (len(v) - 2) + v[-1]


def configure_error_handlers(app):
    @app.errorhandler(403)
    def forbidden_page(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error_page(error):
        return render_template("errors/500.html"), 500
