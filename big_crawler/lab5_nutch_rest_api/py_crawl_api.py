# -*- coding: utf-8 -*-
"""
Created on Thu May 17 09:12:48 2018

@author: j.ischebeck
"""

import requests
import time
from random import randint
NUTCH_URL = 'http://159.122.175.139:30081'

class ApiError:
    def __init__(self, error):
        self.error=error

test_id = "1234567"
#%%

# Seed


seed = {"id": test_id,"name": "doandodge1","seedUrls": [{"id": 1,"seedList": None,
       "url": "http://www.region-suedostoberbayern.bayern.de/verbandsarbeit/sitzungen/"} ]}  #http://www.region-suedostoberbayern.bayern.de/verbandsarbeit/sitzungen/

resp = requests.post(NUTCH_URL+'/seed/create', json=seed)
if resp.status_code != (201 and 200):
    raise ApiError('POST /seed/create/ {}'.format(resp.status_code))

print('Created Seed. ID: {}'.format(resp.text))

#%%
seedDir = resp.text #"/tmp/1526547667623-0"  # comes from first request  1526463295128-0
crawl_id = "sample-crawl-01"


# inject
job_def = {"args": {"seedDir": seedDir}, "confId":"default", "crawlId":crawl_id, "type": "INJECT"}

resp = requests.post(NUTCH_URL+'/job/create', json=job_def)
if resp.status_code != (201 and 200):
    raise ApiError('POST /job/create/ {}'.format(resp.status_code))

print('Created Job data: {}'.format(resp.text))


n = 5


for x in range(0, 5):
    time1 = round(time.time())
    batch = str(time1) + "-" + str(randint(1000, 9999))
    generate = {"args": {     "normalize": False, "filter": True,"crawlId": crawl_id, "curTime": time1, "batch": batch}, "confId":"default","crawlId":crawl_id, "type": "GENERATE"}
    resp_generate = requests.post(NUTCH_URL + '/job/create', json=generate)

    fetch = {"args": {"threads": 50, "crawlId" : crawl_id, "batch" : batch},"confId":"default","crawlId":crawl_id ,"type": "FETCH"}
    resp_fetch = requests.post(NUTCH_URL + '/job/create', json=fetch)

    parse = {"args": {"crawlId" : crawl_id, "batch" : batch}, "confId":"default","crawlId":crawl_id ,"type": "PARSE"}
    resp_parse = requests.post(NUTCH_URL + '/job/create', json=parse)

    updatedb = {"args": {"crawlId" : crawl_id, "batch" : batch },"confId":"default", "crawlId":crawl_id ,"type": "UPDATEDB"}
    resp_updatedb = requests.post(NUTCH_URL+'/job/create', json=updatedb)
#%%
