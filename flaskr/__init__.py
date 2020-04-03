import logging
import os
import sys
from flask import Flask
from flaskr.flaskapp import FlaskApp

def create_app(test_config=None):

    # create and configure the app
    app = FlaskApp(__name__, instance_relative_config=True)
    if "CYGNUM_CONFIG" in os.environ:
        app.config.from_envvar("CYGNUM_CONFIG") # Set in cygnum[-xxx].service

    is_gunicorn = "gunicorn" in os.environ.get("SERVER_SOFTWARE", "")
    if is_gunicorn:
        gunicorn_logger = logging.getLogger("gunicorn.error")
        app.logger.handlers = gunicorn_logger.handlers

    loglevel = app.config['LOGLEVEL']
    app.logger.setLevel(loglevel)
    # logging.basicConfig(level=loglevel,format='(%(threadName)-10s) %(message)s',)
    app.logger.debug("create app")
    
    from flaskr import handler
    app.register_blueprint(handler.bp)

    return app