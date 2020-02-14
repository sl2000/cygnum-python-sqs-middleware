from flask import Flask
import logging
import os
import threading
import uuid

class FlaskApp(Flask):

    OB_VERSION = "200205"

    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)

        self.config.from_pyfile('config.py')
        logging.info(self.config)

        self.TIMEOUT = self.config.get('TIMEOUT',300)

        # ensure the instance folder exists
        try:
            os.makedirs(self.instance_path)
        except OSError:
            pass

        self.rqcntr = 0
        self.rqcntr_lock = threading.Lock()