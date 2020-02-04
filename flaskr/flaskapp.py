from flask import Flask
import boto3
import logging
import os
import threading
import uuid

from flaskr.sqs import sqs

class FlaskApp(Flask):

    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)
        logging.debug("started!")
        logging.debug("pid="+str(os.getpid()))

        self.config.from_pyfile('config.py', silent=True)
        logging.debug(self.config)

        # ensure the instance folder exists
        try:
            os.makedirs(self.instance_path)
        except OSError:
            pass

        self.sqs = sqs(self.config)
        self.rqcntr = 0
        self.rqcntr_lock = threading.Lock()
        
        logging.debug("thats all done.")