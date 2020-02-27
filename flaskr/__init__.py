import logging
import os
from flask import Flask
from flaskr.flaskapp import FlaskApp

def create_app(test_config=None):

    # create and configure the app
    app = FlaskApp(__name__, instance_relative_config=True)

    loglevel = app.config['LOGLEVEL']
    logging.basicConfig(level=loglevel,format='(%(threadName)-10s) %(message)s',)
    logging.debug("create app")
    
    from flaskr import handler
    app.register_blueprint(handler.bp)

    return app