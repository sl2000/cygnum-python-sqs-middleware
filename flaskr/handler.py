from flask import Flask, Blueprint, current_app, jsonify, make_response, request, Response
import base64
import botocore
from connection_pool import ConnectionPool
import html
import json
import logging
import os
from pysqs_extended_client.SQSClientExtended import SQSClientExtended
import threading
import time
import uuid


from flaskr.flaskapp import FlaskApp
from flaskr.sqs import sqs_cl

bp = Blueprint('handler', __name__)

@bp.route('/<app>/config-8f7fc8b1-69f6-4559-951e-97e1cfb73847/')
def return_config(app):
    response = {
        "ACCOUNTS": current_app.config['ACCOUNTS'],        
        "AWS_KEY": current_app.config['AWS_ACCESS_KEY'],
        "BUCKET_NAME": current_app.config['BUCKET_NAME'],
        "UNIDATA_SERVER_ID": current_app.config['UNIDATA_SERVER_ID']
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

@bp.route('/<app>/ob.aspx/<acnt>/', methods=['POST', 'GET', 'PATCH', 'PUT', 'DELETE'])
@bp.route('/<app>/ob.aspx/<acnt>/<path:path>', methods=['POST', 'GET', 'PATCH', 'PUT', 'DELETE'])
def handler(app, acnt, path=None):
    current_app.logger.info("!!!!!!! request received")
    with current_app.rqcntr_lock:
        reqn = current_app.rqcntr + 1
        current_app.rqcntr = reqn
    cp_start = time.time()
    with current_app.sqs_pool.item() as sqs:
        cp_q_durn = time.time() - cp_start
        sqs.reqn += 1
        current_app.logger.info(str(reqn)+" got sqs reqn="+str(sqs.reqn)+" wait="+str(cp_q_durn))

        http = {
            "URL": request.url,
            "HTTPS": ("on" if request.is_secure else "off"),
            "REQUEST_METHOD": request.method,
            "PATH_INFO": request.path,
            "QUERY_STRING": request.query_string.decode(),
            "REMOTE_ADDR": request.remote_addr,
            "SERVER_NAME": sqs.server_name,
            "X_CACI_IID": current_app.OB_VERSION + " " + str(os.getpid()) + " " + str(threading.get_ident()) + "q" + str(sqs.reqn) + "a" + str(reqn)
        }
        for header in request.headers.items():
            http["HTTP_"+header[0].upper()] = header[1]

        v = http.get("HTTP_X-FORWARDED-REMOTE-ADDR")
        if v:
            http["REMOTE_ADDR"] = v
            del http["HTTP_X-FORWARDED-REMOTE-ADDR"]

        v = http.get("HTTP_X-FORWARDED-PROTO")
        if v:
            http["HTTPS"] = "on" if v == "https" else "off"
            del http["HTTP_X-FORWARDED-PROTO"]
            
        post_data = request.get_data()
        queue_resp = sqs.get_queue_resp()
        
        current_app.logger.info(str(reqn)+' queue='+queue_resp+" qreqn="+str(sqs.reqn))

        req = {
            "QUEUE_RESP": queue_resp,
            "REQ_NUM": reqn,
            "POST_DATA": base64.encodebytes(post_data).decode(),
            "HTTP": http
        }
        str_req = json.dumps(req)

        if acnt not in sqs.queue_rqs:
            return make_response('Account '+html.escape(acnt)+' not valid.', 404)

        queue_req = sqs.queue_rqs[acnt]

        r = sqs.sqs_client.send_message(queue_req, str_req, {})
        current_app.logger.info(str(reqn)+" send to "+queue_req+" reply to "+queue_req+" reqn="+str(reqn)+" threadid="+str(threading.get_ident()))
        while True:
            wait_last_contact = time.time()
            while True:
                current_app.logger.info(str(reqn)+" waiting for reply")
                try:
                    message = sqs.sqs_client.receive_message(queue_resp,1,20)
                except Exception as err:
                    etxt =  "Failed to read from queue "+sqs.queue_resp_name+". Err="+str(err)
                    current_app.logger.error(err)
                    sqs.create_resp_queue()
                    return etxt, 500
                current_app.logger.info(str(reqn)+" "+str(repr(message))[0:200])
                if message is None:
                    current_app.logger.info(str(reqn)+" No reply after " + str(time.time() - wait_last_contact))
                    if (time.time() - wait_last_contact) > current_app.TIMEOUT:
                        return "No response from database server (time="+str(time.time() - wait_last_contact)+")", 500
                    continue
                break
            
            message = message[0]
            receipt_handle = message['ReceiptHandle']

            try:
                sqs.sqs_client.delete_message(queue_resp, receipt_handle)
            except Exception as err:
                current_app.logger.error(err)
                sqs.create_resp_queue()

            try:
                reply = json.loads(message['Body'])
            except:
                return "failed to parse reply as json - probably too big "+message['Body'], 500

            current_app.logger.info(str(reqn)+' Received and deleted message reqn=' + str(reply['REQ_NUM']) + ' on '+" threadid="+str(threading.get_ident()))
            reply_reqn = reply['REQ_NUM']
            if (reply_reqn != reqn and reply_reqn != "CRASH"):
                if (reply_reqn == "PING"):
                    current_app.logger.info(str(reqn)+' PING so wait')
                    continue
                return "request number mismatch "+str(reqn)+message['Body'], 500
            body = reply['RESPONSE']
            headers = reply['HEADERS']
            break

        response = make_response()
        rheaders = response.headers
        status = 200
        cache = False
        current_app.logger.info(str(reqn)+' Complete')

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
        elif lname == "cache":
            cache = True
        elif lname == "cache-control":
            if val == "No-Cache":
                cache = False
            # ignore other cache control headers - we're either cached or not
        elif lname == "status":
            status = int(val)
        elif lname == "x-tco-version":
            rheaders.set(name, val + " CACI=" + OB_VERSION+ " PYTHON="+sys.version)
        elif lname == "redirect":
            status = 302
            rheaders.set('Location', val)
        elif lname == "set-cookie":
            rheaders.add(name,val)
        elif lname == "x-sleep":
            time.sleep(int(val)/1000)
        else:
            rheaders.set(name,val)

    if cache:
        response.cache_control.public = True
        response.cache_control.max_age = 31536000
    else:
        response.cache_control.private = True

    response.data = body
    
    return response, status