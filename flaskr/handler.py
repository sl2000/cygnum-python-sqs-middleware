from flask import Flask, escape, Blueprint, current_app, jsonify, make_response, request, Response
import base64
import json
import logging
from pysqs_extended_client.SQSClientExtended import SQSClientExtended
import threading
import time
import uuid

from flaskr.flaskapp import FlaskApp
from flaskr.sqs import sqs_cl

bp = Blueprint('handler', __name__)

@bp.route('/config/')
def return_config():
    response = {
        "UNIDATA_SERVER_ID": current_app.config['UNIDATA_SERVER_ID'],
        "BUCKET_UNQ": current_app.config['BUCKET_UNQ']
    }
    return response

@bp.route('/test-stream/')
def test_stream():
    def generate():
        i = 0
        while i < 60:
            print(i)
            yield "line " + str(i) + "<br>"
            i += 1
            time.sleep(1)
    return Response(generate())

@bp.route('/tcowebsu/ob.aspx/<acnt>/', methods=['POST', 'GET', 'PATCH', 'PUT', 'DELETE'])
@bp.route('/tcowebsu/ob.aspx/<acnt>/<path:path>', methods=['POST', 'GET', 'PATCH', 'PUT', 'DELETE'])
def handler(acnt, path=None):
    sqs = None
    thread_data = threading.local()
    try:
        sqs = thread_data.sqs
        logging.info("!!!!!!! got existing sqs")
    except AttributeError:
        logging.info("!!!!!!! create new sqs")
        sqs = sqs_cl(current_app.config)
        thread_data.sqs = sqs
    sqs = thread_data.sqs
    logging.info('!!!!! queue='+sqs.queue_resp)

    with current_app.rqcntr_lock:
        reqn = current_app.rqcntr + 1
        current_app.rqcntr = reqn

    http = {
        "URL": request.url,
        "HTTPS": ("on" if request.is_secure else "off"),
        "REQUEST_METHOD": request.method,
        "PATH_INFO": request.path,
        "QUERY_STRING": request.query_string.decode(),
        "REMOTE_ADDR": request.remote_addr
    }
    for header in request.headers.items():
        http["HTTP_"+header[0].upper()] = header[1]
    req = {
        "QUEUE_RESP": sqs.queue_resp,
        "REQ_NUM": reqn,
        "POST_DATA": base64.b64encode(request.get_data()).decode(),
        "HTTP": http
    }
    str_req = json.dumps(req)

    if acnt not in sqs.queue_rqs:
        return make_response('Account '+escape(acnt)+' not valid.', 404)

    queue_req = sqs.queue_rqs[acnt]

    r = sqs.sqs_client.send_message(queue_req, str_req, {})
    logging.info("!!!!!!!! send to "+queue_req+" reply to "+queue_req+" reqn="+str(reqn)+" threadid="+str(threading.get_ident()))

    while True:
        logging.info("waiting for reply")
        message = sqs.sqs_client.receive_message(sqs.queue_resp,1,20)
        logging.info(str(repr(message))[0:200])
        if message is None:
            continue
        break
    
    message = message[0]
    receipt_handle = message['ReceiptHandle']

    sqs.sqs_client.delete_message(sqs.queue_resp, receipt_handle)

    try:
        reply = json.loads(message['Body'])
    except:
        return "failed to parse reply as json - probably too big "+message['Body']

    logging.info('Received and deleted message reqn=' + str(reply['REQ_NUM']) + ' on '+" threadid="+str(threading.get_ident()))
    if (reply['REQ_NUM'] != reqn):
        return "request number mismatch "+str(reqn)+message['Body']
    body = reply['RESPONSE']
    headers = reply['HEADERS']

    response = make_response()
    rheaders = response.headers

    for header in headers.split('\xFD'):
        header = header.split('\xFC')
        name = header[0]
        if len(header) >= 2:
            val = header[1]
        else:
            val = ""

        lname = name.lower()
        if lname == "binary":
            body = base64.b64decode(body)
        elif lname == "something else":
            pass
        else:
            rheaders[name] = val

    response.data = body
    
    return response