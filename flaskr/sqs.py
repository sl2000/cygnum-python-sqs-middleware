import atexit
from datetime import date
from flask import current_app
import logging
import os
import platform
import boto3
import sqs_extended_client
import threading
import time
from uuid import uuid4

class sqs_cl():

    n_resp_queue = 0

    def __init__(self):
        self.log("!!!!!!! create new sqs")

        atexit.register(self.cleanup) # This works with real threading - but not with eventlet

        config = current_app.config

        # self.sqs_client = SQSClientExtended(config['AWS_ACCESS_KEY'], config['AWS_SECRET_KEY'], config['AWS_REGION'], config['BUCKET_NAME'])
        self.sqs_extended_client = boto3.client("sqs",aws_access_key_id=config['AWS_ACCESS_KEY'], aws_secret_access_key=config['AWS_SECRET_KEY'], region_name=config['AWS_REGION'])
        self.sqs_extended_client.s3_client = boto3.client("s3",aws_access_key_id=config['AWS_ACCESS_KEY'], aws_secret_access_key=config['AWS_SECRET_KEY'], region_name=config['AWS_REGION'])
        self.sqs_extended_client.large_payload_support = config['BUCKET_NAME']
        self.queue_rqs = {}
        for acnt in config['ACCOUNTS']:
            req_qname = (
                "cyg"
                + "-" + config['UNIDATA_SERVER_ID'].replace("-","_")
                + "-rq"
                + "-" + acnt
            )
            queue = self.sqs_extended_client.get_queue_url(QueueName = req_qname)['QueueUrl']
            self.log("got existing queue "+queue)
            self.queue_rqs[acnt] = queue

        self.create_resp_queue()
        self.server_name = platform.node()
        self.reqn = 0
        self.queue_failed = False

    def __del__(self):
        self.cleanup()

    def get_queue_resp(self):
        idle_time = time.time() - self.last_qtime
        if self.queue_failed:
            self.create_resp_queue()
            self.queue_failed = False
        elif idle_time >= 120:
            # Check that can read from queue - otherwise create a new one
            # Copes with queue being deleted by server tidy up process
            try:
                dummy = self.sqs_extended_client.receive_message(QueueUrl=self.queue_resp,MaxNumberOfMessages=1,WaitTimeSeconds=0)
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
            # + "-" + str(threading.get_ident())
            + "-" + str(self.n_resp_queue)
            + "-" + str(uuid4())
        )[0:80]
        resp_qname = resp_qname.replace(".","_")
        self.queue_resp_name = resp_qname
        self.queue_resp = self.__get_queue(resp_qname)
        self.last_qtime = time.time()

    def __get_queue(self, queue_name):
        try:
            queue = self.sqs_extended_client.create_queue(
                QueueName = queue_name,
                Attributes = {
                    'MessageRetentionPeriod': '300',
                    'SqsManagedSseEnabled': 'true'
                }
            )
            self.log("created new queue "+queue_name)
        except:
            queue = self.sqs_extended_client.get_queue_url(QueueName = queue_name)
            self.log("got existing queue "+queue_name)
        return queue['QueueUrl']

    def reset(self):
        # I hoped connection pool did this but no
        self.cleanup()

    def cleanup(self):
        self.log("cleanup")
        if ('cyg-resp1' in self.queue_resp):
            return
        try:
            self.sqs_extended_client.delete_queue(QueueUrl=self.queue_resp)
            self.log("deleted queue "+self.queue_resp)
        except:
            self.log("failed to delete queue "+self.queue_resp)
            pass

    def log(self, message):
        try:
            current_app.logger.info(message)
        except:
            pass
