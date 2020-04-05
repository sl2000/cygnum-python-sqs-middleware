from flask import Flask
from connection_pool import ConnectionPool
import logging
import os
import threading
import uuid

from flaskr.sqs import sqs_cl

class FlaskApp(Flask):

    OB_VERSION = "200405"

    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)

        # ensure the instance folder exists
        try:
            os.makedirs(self.instance_path)
        except OSError:
            pass

        self.rqcntr = 0
        self.rqcntr_lock = threading.Lock()
        self.sqs_pool = ConnectionPool(
            create=lambda: sqs_cl(),
            max_size=50,
            max_usage=100000,
            idle=1800,
            ttl=60
        )