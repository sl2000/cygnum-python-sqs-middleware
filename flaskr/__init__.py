import logging
import os
from flask import Flask
from flaskr.flaskapp import FlaskApp

def create_app(test_config=None):

    logging.basicConfig(level=logging.DEBUG,format='(%(threadName)-10s) %(message)s',)
    logging.debug("create app")

    # create and configure the app
    app = FlaskApp(__name__, instance_relative_config=True)
    
    from flaskr import handler
    app.register_blueprint(handler.bp)

    return app