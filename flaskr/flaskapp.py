from flask import Flask
import logging
import os
import threading
import uuid

class FlaskApp(Flask):

    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)

        self.config.from_pyfile('config.py', silent=True)
        logging.info(self.config)

        # ensure the instance folder exists
        try:
            os.makedirs(self.instance_path)
        except OSError:
            pass

        self.rqcntr = 0
        self.rqcntr_lock = threading.Lock()