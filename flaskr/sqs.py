import atexit
from datetime import date
import logging
import os
from pysqs_extended_client.SQSClientExtended import SQSClientExtended
import threading
import uuid

class sqs_cl():

    def __init__(self, config):
        self.log("thread starting "+str(threading.get_ident()))

        atexit.register(self.cleanup)

        self.sqs_client = SQSClientExtended(config['AWS_ACCESS_KEY'], config['AWS_SECRET_KEY'], config['AWS_REGION'], config['BUCKET_NAME'])
        
        self.queue_rqs = {}
        for acnt in config['ACCOUNTS']:
            req_qname = 'cyg-rq-' + config['UNIDATA_SERVER_ID'] + '-' + acnt
            self.queue_rqs[acnt] = self.__get_queue(req_qname)

        resp_qname = 'cyg-resp-'+date.today().strftime("%Y%m%d")+"-"+str(os.getpid()) + "-" + str(threading.get_ident()) + "-" + str(uuid.uuid1())
        self.queue_resp = self.__get_queue(resp_qname)

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
        self.log("cleanup!!")
        if ('cyg-resp1' in self.queue_resp):
            return
        try:
            self.sqs_client.sqs.delete_queue(QueueUrl=self.queue_resp)
            self.log("deleted queue "+self.queue_resp)
        except:
            self.log("failed to delete queue "+self.queue_resp)
            pass

    def log(self, message):
        print(message)

