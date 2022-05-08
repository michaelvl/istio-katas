#!/usr/bin/env python

import os
import flask
import prometheus_client
import datetime, time
import logging
import random
import re
from concurrent import futures
import grpc

import age_pb2
import age_pb2_grpc
import name_pb2
import name_pb2_grpc

random_app = flask.Flask('random')
#age_app = flask.Flask('age')
#name_app = flask.Flask('name')
sentence_app = flask.Flask('sentence')

port = int(os.getenv('SVC_PORT', 5000))
metrics_port = int(os.getenv('SVC_METRICS_PORT', 8000))
authentication_bug_probability = float(os.getenv('SENTENCE_AUTH_BUG_PROBABILITY', 0.0))
min_age = int(os.getenv('SENTENCE_AGE_MIN', 0))
max_age = int(os.getenv('SENTENCE_AGE_MAX', 100))
names = os.getenv('SENTENCE_NAMES', 'Peter,Ray,Egon').split(',')
svc_delay_min = float(os.getenv('SENTENCE_SVC_DELAY_MIN', 0.0))
svc_delay_max = float(os.getenv('SENTENCE_SVC_DELAY_MAX', 0.0))
mode = os.getenv('SENTENCE_MODE', 'age')
age_svc_url = os.getenv('SENTENCE_AGE_SVC_URL', 'age:5000')
name_svc_url = os.getenv('SENTENCE_NAME_SVC_URL', 'name:5000')
random_svc_url = os.getenv('SENTENCE_RANDOM_SVC_URL', '')
random_svc_url2 = os.getenv('SENTENCE_RANDOM_SVC_URL2', '')
random_svc2_probability = float(os.getenv('SENTENCE_RANDOM_SVC2_PROBABILITY', 0.0))

auth_z_bug_value = '12345'

fwd_headers = ['x-request-id',
               'x-b3-traceid',
               'x-b3-spanid',
               'x-b3-parentspanid',
               'x-b3-sampled',
               'x-b3-flags',
               'b3',
               'x-client-trace-id',
               'x-envoy-force-trace',
               # Custom headers
               'x-test',
               'authorization']

class timed():
    def __init__(self, txt):
        self.txt = txt
    def __enter__(self):
        self.start = datetime.datetime.now()
    def __exit__(self, exc_type, exc_value, exc_traceback):
        end = datetime.datetime.now()
        took = (end-self.start).total_seconds()*1000
        logging.warning("Operation '{}' took {:.3f}ms".format(self.txt, took))

def get_random_int(xmin, xmax):
    if random_svc_url:
        random_url = random_svc_url
        if random_svc_url2:
            p = float(random.randint(0,100))/100.0
            if p < random_svc2_probability:
                random_url = random_svc_url2
        with timed('random') as t:
            hdrs = get_fwd_headers()
            logging.warning('Forwarding headers {}'.format(hdrs))
            r = requests.get(random_url, timeout=1, headers=hdrs)
            if r.status_code != 200:
                flask.abort(r.status_code)
            logging.warning("Used random-svc URL {}. Got '{}'".format(random_url, r.text))
            if re.match('\d+' ,r.text):
                val = int(r.text)
            else:
                val = ord(r.text)
        return xmin + (val % (xmax-xmin+1))
    else:
        return random.randint(xmin, xmax)

def get_random_age():
    return get_random_int(min_age, max_age)

def get_random_name():
    nidx = get_random_int(0, len(names)-1)
    return names[nidx]
        
def do_random_delay():
    d = svc_delay_min + random.random()*(svc_delay_max-svc_delay_min)
    if d > 0:
        logging.warning('Delay {}s'.format(d))
        time.sleep(d)

def flask_lc_headers():
    return {k.lower(): v for k,v in flask.request.headers.items()}
    
def get_fwd_headers():
    in_hdrs = flask_lc_headers()
    return { h: v for h,v in in_hdrs.items() if h.lower() in fwd_headers}

@random_app.route('/')
def get_random():
    with timed('random') as t:
        do_random_delay()
        in_hdrs = flask_lc_headers()
        if 'authorization' not in in_hdrs or in_hdrs['authorization'] == auth_z_bug_value:
            logging.warning('Simulating bug due to missing/bad authZ header. Got headers: {}'.format(in_hdrs))
            time.sleep(0.7)
        m_requests.labels('random').inc()
        r = random.randint(0, 10000)
        logging.warning("Using random '{}'".format(r))
    return str(r)

class AgeService(age_pb2_grpc.AgeServicer):
    def GetAge(self, request, context):
        with timed('age') as t:
            do_random_delay()
            m_requests.labels('age').inc()
            age = get_random_age()
            logging.warning("Using age '{}'".format(age))
        return age_pb2.AgeReply(age=age)

def age_serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    age_pb2_grpc.add_AgeServicer_to_server(AgeService(), server)
    insec_port = '[::]:'+str(port)
    logging.warning('Serving on '+insec_port)
    server.add_insecure_port(insec_port)
    server.start()
    server.wait_for_termination()

class NameService(name_pb2_grpc.NameServicer):
    def GetName(self, request, context):
        with timed('name') as t:
            do_random_delay()
            m_requests.labels('name').inc()
            name = get_random_name()
            logging.warning("Using name '{}'".format(name))
        return name_pb2.NameReply(name=name)

def name_serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    name_pb2_grpc.add_NameServicer_to_server(NameService(), server)
    insec_port = '[::]:'+str(port)
    logging.warning('Serving on '+insec_port)
    server.add_insecure_port(insec_port)
    server.start()
    server.wait_for_termination()

#@name_app.route('/choices')
#def get_name_choices():
#    return str(names)

@sentence_app.route('/')
def get_sentence():
    with timed('sentence') as t:
        do_random_delay()
        hdrs = get_fwd_headers()
        # Simulate authentication and possibly bug
        p = float(random.randint(0,100))/100.0
        if p < authentication_bug_probability:
            logging.warning('Simulating authentication bug (p={}) - adding wrong header'.format(p))
            hdrs['authorization'] = auth_z_bug_value
        else:
            hdrs['authorization'] = 'something-valid'
        metadata = tuple([(k,v) for k,v in hdrs.items()])
        logging.warning('Forwarding metadata (headers) {}'.format(metadata))
        with grpc.insecure_channel(age_svc_url) as channel:
            stub = age_pb2_grpc.AgeStub(channel)
            response = stub.GetAge(age_pb2.AgeRequest(unused=42), metadata=metadata)
            age = str(response.age)
        with grpc.insecure_channel(name_svc_url) as channel:
            stub = name_pb2_grpc.NameStub(channel)
            response = stub.GetName(name_pb2.NameRequest(unused=42), metadata=metadata)
            name = str(response.name)
        m_requests.labels('sentence').inc()
    return '{} is {} years'.format(name, age)

if __name__ == '__main__':

    host = "0.0.0.0"

    m_requests = prometheus_client.Counter('sentence_requests_total',
                                           'Number of requests', ['type'])
    prometheus_client.start_http_server(metrics_port)

    if mode=='random':
        random_app.run(host=host, port=port)
    elif mode=='age':
        age_serve()
    elif mode=='name':
        name_serve()
    elif mode=='sentence':
        logging.warning('Using gRPC for sub-services')
        sentence_app.run(host=host, port=port)
