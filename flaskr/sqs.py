import atexit
from datetime import date
from flask import current_app
import logging
import os
import platform
from pysqs_extended_client.SQSClientExtended import SQSClientExtended
import threading
import time

class sqs_cl():

    def __init__(self):
        self.log("thread starting "+str(threading.get_ident()))

        atexit.register(self.cleanup)

        config = current_app.config

        self.sqs_client = SQSClientExtended(config['AWS_ACCESS_KEY'], config['AWS_SECRET_KEY'], config['AWS_REGION'], config['BUCKET_NAME'])
        self.sqs_client.set_always_through_s3(False)
        
        self.queue_rqs = {}
        for acnt in config['ACCOUNTS']:
            req_qname = (
                "cyg"
                + "-" + config['UNIDATA_SERVER_ID'].replace("-","_")
                + "-rq"
                + "-" + acnt
            )
            self.queue_rqs[acnt] = self.__get_queue(req_qname)

        self.n_resp_queue = 0
        self.create_resp_queue()
        self.server_name = platform.node()

    def get_queue_resp(self):
        idle_time = time.time() - self.last_qtime
        if idle_time >= 120:
            # Check that can read from queue - otherwise create a new one
            # Copes with queue being deleted by server tidy up process
            try:
                dummy = self.sqs_client.receive_message(self.queue_resp,1,0)
            except:
                self.create_resp_queue()
        self.last_qtime = time.time()
        return self.queue_resp

    def create_resp_queue(self):
        config = current_app.config
        self.n_resp_queue += 1
        resp_qname = (
            "cyg"
            + "-" + config['UNIDATA_SERVER_ID'].replace("-","_")
            + "-resp"
            + "-" + platform.node().replace("-","_")
            + "-" + date.today().strftime("%Y%m%d")
            + "-" + str(os.getpid())
            + "-" + str(threading.get_ident())
            + "-" + str(self.n_resp_queue)
        )
        resp_qname = resp_qname.replace(".","_")
        self.queue_resp_name = resp_qname
        self.queue_resp = self.__get_queue(resp_qname)
        self.last_qtime = time.time()

    def __get_queue(self, queue_name):
        try:
            queue = self.sqs_client.sqs.create_queue(
                QueueName = queue_name,
                Attributes = {
                    'MessageRetentionPeriod': '300'
                }
            )
            self.log("created new queue "+queue_name)
        except:
            queue = self.sqs_client.sqs.get_queue_url(QueueName = queue_name)
            self.log("got existing queue "+queue_name)
        return queue['QueueUrl']

    def cleanup(self):
        self.log("cleanup")
        if ('cyg-resp1' in self.queue_resp):
            return
        try:
            self.sqs_client.sqs.delete_queue(QueueUrl=self.queue_resp)
            self.log("deleted queue "+self.queue_resp)
        except:
            self.log("failed to delete queue "+self.queue_resp)
            pass

    def log(self, message):
        logging.info(message)

