from flask import Flask, escape, Blueprint, current_app, jsonify, make_response, request, Response
import base64
import json
import logging
import threading
import time
import uuid

from flaskr.flaskapp import FlaskApp

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
    sqs = current_app.sqs
    with current_app.rqcntr_lock:
        current_app.rqcntr += 1
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
        "REQ_NUM": current_app.rqcntr,
        "POST_DATA": base64.b64encode(request.get_data()).decode(),
        "HTTP": http
    }
    str_req = json.dumps(req)

    if acnt not in sqs.queue_rqs:
        return make_response('Account '+escape(acnt)+' not valid.', 404)

    queue_req = sqs.queue_rqs[acnt]

    r = sqs.boto3_client.send_message(
        QueueUrl=queue_req,
        MessageBody=str_req
    )
    logging.debug("send to "+queue_req+" reply to "+queue_req+" reqn="+str(current_app.rqcntr)+" threadid="+str(threading.get_ident()))

    while True:
        logging.debug("waiting for reply")
        r = sqs.boto3_client.receive_message(
            QueueUrl=sqs.queue_resp,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20
        )
        logging.debug(str(repr(r))[0:200])
        if "Messages" not in r:
            logging.debug("not messages")
            continue
        message = r['Messages'][0]
        if not message:
            logging.debug("not message")
            continue
        break
    
    receipt_handle = message['ReceiptHandle']

    sqs.boto3_client.delete_message(
        QueueUrl=sqs.queue_resp,
        ReceiptHandle=receipt_handle
    )

    try:
        reply = json.loads(message['Body'])
    except:
        return "failed to parse reply as json - probably too big "+message['Body']

    logging.debug('Received and deleted message reqn=' + str(reply['REQ_NUM']) + ' on '+" threadid="+str(threading.get_ident()))
    if (reply['REQ_NUM'] != current_app.rqcntr):
        return "request number mismatch "+str(current_app.rqcntr)+message['Body']
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