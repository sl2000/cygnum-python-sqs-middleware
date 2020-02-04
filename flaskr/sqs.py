import atexit
import boto3
from datetime import date
import logging
import os
import threading
import uuid

class sqs(threading.local):

    def __init__(self, config):
        atexit.register(self.cleanup)

        self.boto3_client = boto3.client(
            'sqs',
            aws_access_key_id=config['AWS_ACCESS_KEY'],
            aws_secret_access_key=config['AWS_SECRET_KEY']
        )
        logging.debug("thread started")
        logging.debug("aws stuff="+config['AWS_ACCESS_KEY']+" / "+config['AWS_SECRET_KEY'])
        
        self.queue_rqs = {}
        for acnt in config['ACCOUNTS']:
            req_qname = 'cyg-rq-' + config['UNIDATA_SERVER_ID'] + '-' + acnt
            self.queue_rqs[acnt] = self.__get_queue(req_qname)

        resp_qname = 'cyg-resp-'+date.today().strftime("%Y%m%d")+"-"+str(os.getpid()) + "-" + str(threading.get_ident()) + "-" + str(uuid.uuid1())
        self.queue_resp = self.__get_queue(resp_qname)

    def __get_queue(self, queue_name):
        try:
            queue = self.boto3_client.create_queue(
                QueueName = queue_name,
                Attributes = {
                    'MessageRetentionPeriod': '300'
                }
            )
            logging.debug("created new queue "+queue_name)
        except:
            queue = self.boto3_client.get_queue_url(QueueName = queue_name)
            logging.debug("got existing queue "+queue_name)
        return queue['QueueUrl']

    def cleanup(self):
        logging.debug("cleanup!!")
        if ('cyg-resp1' in self.queue_resp):
            return
        try:
            self.boto3_client.delete_queue(QueueUrl=self.queue_resp)
            logging.debug("deleted queue "+self.queue_resp)
        except:
            logging.debug("failed to delete queue "+self.queue_resp)

