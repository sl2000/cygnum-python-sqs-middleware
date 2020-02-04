from flask import Flask
import logging
import os
import threading
import uuid

#from flaskr.sqs import sqs

class FlaskApp(Flask):

    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)
        self.logger.setLevel(logging.WARNING)
        logging.info("started!")
        logging.info("pid="+str(os.getpid()))

        self.config.from_pyfile('config.py', silent=True)
        logging.info(self.config)

        # ensure the instance folder exists
        try:
            os.makedirs(self.instance_path)
        except OSError:
            pass

        #self.sqs = sqs(self.config)
        self.rqcntr = 0
        self.rqcntr_lock = threading.Lock()
        
        logging.info("thats all done.")