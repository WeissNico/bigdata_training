# -*- coding: utf-8 -*-
"""
Created on Thu May 17 09:12:48 2018

@author: j.ischebeck
"""

import requests

NUTCH_URL = 'http://159.122.175.139:30081'

class ApiError:
    def __init__(self, error):
        self.error=error

test_id = "123456"
#%%

# Seed


seed = {"id": test_id,"name": "doandodge1","seedUrls": [{"id": 1,"seedList": None,
       "url": "http://nutch.apache.org/"} ]}  #http://www.region-suedostoberbayern.bayern.de/verbandsarbeit/sitzungen/

resp = requests.post(NUTCH_URL+'/seed/create', json=seed)
if resp.status_code != (201 and 200):
    raise ApiError('POST /seed/create/ {}'.format(resp.status_code))

print('Created Seed. ID: {}'.format(resp.text))

#%%
seedDir = resp.text #"/tmp/1526547667623-0"  # comes from first request  1526463295128-0
crawl_id = "sample-crawl-01"

# inject
job_def = {"args": {"seedDir": seedDir },"crawlId":crawl_id ,"type": "INJECT"}

resp = requests.post(NUTCH_URL+'/job/create', json=job_def)
if resp.status_code != (201 and 200):
    raise ApiError('POST /job/create/ {}'.format(resp.status_code))

print('Created Job data: {}'.format(resp.text))

generate = {"args": {"seedDir": seedDir },"crawlId":crawl_id ,"type": "GENERATE"}
fetch = {"args": {"seedDir": seedDir },"crawlId":crawl_id ,"type": "FETCH"}
parse = {"args": {"seedDir": seedDir },"crawlId":crawl_id ,"type": "PARSE"}
updatedb = {"args": {"seedDir": seedDir },"crawlId":crawl_id ,"type": "UPDATEDB"}

#%%
