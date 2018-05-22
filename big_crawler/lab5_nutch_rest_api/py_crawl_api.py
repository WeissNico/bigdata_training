# -*- coding: utf-8 -*-
"""
Created on Thu May 17 09:12:48 2018

@author: j.ischebeck
"""

import requests
import time
from random import randint
import json
NUTCH_URL = 'http://159.122.175.139:30081'

class ApiError:
    def __init__(self, error):
        self.error=error

test_id = "12348"

# Seed

def getJobStatus(jobid, seedDir, config):
    resp_status = requests.get(NUTCH_URL+'/job/'+jobid)
    status_json = json.loads(resp_status.text)
    status_msg = status_json['state']
    return status_msg


seed = {"id": test_id,"name": "mynutch","seedUrls": [{"id": 1,"seedList": None,
       "url": "http://www.region-suedostoberbayern.bayern.de/verbandsarbeit/sitzungen/"} ]}  #http://www.region-suedostoberbayern.bayern.de/verbandsarbeit/sitzungen/ http://nutch.apache.org/
# http://nutch.apache.org/     https://www.lra-aoe.de/   https://www.wikipedia.org/
resp = requests.post(NUTCH_URL+'/seed/create', json=seed)
if resp.status_code != (201 and 200):
    raise ApiError('POST /seed/create/ {}'.format(resp.status_code))

print('Created Seed. ID: {}'.format(resp.text))

#%%
seedDir = resp.text #"/tmp/1526547667623-0"  # comes from first request  1526463295128-0
crawl_id = "mynutch"


# inject
job_def = {"args": {"seedDir": seedDir}, "confId":"default", "crawlId":crawl_id, "type": "INJECT"}

resp = requests.post(NUTCH_URL+'/job/create', json=job_def)
if resp.status_code != (201 and 200):
    raise ApiError('POST /job/create/ {}'.format(resp.status_code))

print('Created Job data: {}'.format(resp.text))


config = "default" #resp_config.text #"default"
#print(config)

for x in range(0, 2):
    print(x)
    time1 = int(round(time.time()*1000))
    batch = str(time1) + "-" + str(randint(1000, 9999))
    print(time1)
    #print(batch)
    generate = {"args": {"normalize": False, "filter": True,"crawlId": crawl_id, "curTime": time1, "batch": batch}, "confId":config,"crawlId":crawl_id, "type": "GENERATE"}
    resp_generate = requests.post(NUTCH_URL + '/job/create', json=generate)
    while True:
        msg = getJobStatus(resp_generate.text, seedDir, config)
        if msg == ("FINISHED"):
            print("generate")
            break;
        else:
            time.sleep(1)
    if resp_generate.status_code != (201 and 200):
        raise ApiError('POST /job/create/ {}' + format(resp_generate.status_code))


    fetch = {"args": {"threads": 50, "crawlId" : crawl_id, "batch" : batch},"confId":config,"crawlId":crawl_id ,"type": "FETCH"}
    resp_fetch = requests.post(NUTCH_URL + '/job/create', json=fetch)
    while True:
        msg = getJobStatus(resp_fetch.text, seedDir, config)
        if msg == ("FINISHED"):
            print("fetch")
            break;
        else:
            time.sleep(1)
    if resp_fetch.status_code != (201 and 200):
        raise ApiError('POST /job/create/ {}' + format(resp_fetch.status_code))


    parse = {"args": {"crawlId" : crawl_id, "batch" : batch}, "confId":config,"crawlId":crawl_id ,"type": "PARSE"}
    resp_parse = requests.post(NUTCH_URL + '/job/create', json=parse)
    while True:
        msg = getJobStatus(resp_parse.text, seedDir, config)
        if msg == ("FINISHED"):
            print("parse")
            break;
        else:
            time.sleep(1)
    if resp_parse.status_code != (201 and 200):
        raise ApiError('POST /job/create/ {}' + format(resp_parse.status_code))


    updatedb = {"args": {"crawlId" : crawl_id, "batch" : batch },"confId":config, "crawlId":crawl_id ,"type": "UPDATEDB"}
    resp_updatedb = requests.post(NUTCH_URL+'/job/create', json=updatedb)
    while True:
        msg = getJobStatus(resp_updatedb.text, seedDir, config)
        if msg == ("FINISHED"):
            print("updatedb")
            break;
        else:
            time.sleep(1)
    if resp_updatedb.status_code != (201 and 200):
        raise ApiError('POST /job/create/ {}' + format(resp_updatedb.status_code))

    print("--------------------------")

