import logging

ACCOUNTS = ["ob_live", "ob_train"]
UNIDATA_SERVER_ID = "ken-esdev-01"
TIMEOUT = 60 # Max time to wait for server response
MAX_CONTENT_LENGTH = 16 * 1024 # Max upload size
LOGLEVEL = logging.WARNING
# AWS Settings
BUCKET_NAME = "cygnum.XXX.es.caci.co.uk"
AWS_ACCESS_KEY = ""
AWS_SECRET_KEY = ""
AWS_REGION = "eu-west-2"