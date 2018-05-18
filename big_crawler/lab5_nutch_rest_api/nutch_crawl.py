import requests
import time
from random import randint
NUTCH_URL = 'http://159.122.175.139:30081'


test_id = "12349"

#seed = {"id": test_id,"name": "mynutch","seedUrls": [{"id": 1,"seedList": None,
#       "url": "http://wikipedia.de/"}]}
seed = {
    "id": "12345",
    "name": "doandodge",
    "seedUrls": [
        {
            "id": 1,
            "seedList": None,
            "url": "http://nutch.apache.org/"
        }
    ]
}


resp_seed = requests.post(NUTCH_URL+'/seed/create', json=seed)
seedDir = resp_seed.text
crawl_id = "nutch"


#config =  {"configId":"1c71cd51-b19c-4963-980e-6eb688c54b46","force": "false", "params" : { "nutch.conf.uuid":"1c71cd51-b19c-4963-980e-6eb688c54b46", "mapred.reduce.tasks.speculative.execution":False, "mapred.map.tasks.speculative.execution" : False, "mapred.compress.map.output" : True, "mapred.reduce.tasks" : 2, "fetcher.timelimit.mins": 180, "mapred.skip.attempts.to.start.skipping" : 2, "mapred.skip.map.max.skip.records" : 1,} }
config = {
"configId":"1c71cd51-b19c-4963-980e-6eb688c54b46",
"force": "false",
"params" : {
    "nutch.conf.uuid":"1c71cd51-b19c-4963-980e-6eb688c54b46",
    "mapred.reduce.tasks.speculative.execution":False,
    "mapred.map.tasks.speculative.execution" : False,
    "mapred.compress.map.output" : True,
    "mapred.reduce.tasks" : 2,
    "fetcher.timelimit.mins": 180,
    "mapred.skip.attempts.to.start.skipping" : 2,
    "mapred.skip.map.max.skip.records" : 1,
}
}


resp_config= requests.post(NUTCH_URL+'/config/1c71cd51-b19c-4963-980e-6eb688c54b46', json=config)

config_id = resp_config.text #"1c71cd51-b19c-4963-980e-6eb688c54b46" #"default"
# inject
#job_def = {"args": {"seedDir": seedDir}, "confId":config_id, "crawlId":crawl_id, "type": "INJECT"}
job_def = {
    "args": {
        "seedDir": seedDir
    },
    "confId": config_id,
    "crawlId": "sample-crawl-01",
    "type": "INJECT"
}

resp_job_def = requests.post(NUTCH_URL+'/job/create', json=job_def)

for x in range(0, 5):
    time1 = int(time.time())#round(time.time())
    batch = str(time1) + "-" + str(randint(1000, 9999))
    print(time1)
    generate = {"args": {"normalize": False, "filter": True,"crawlId": crawl_id, "curTime": time1, "batch": batch}, "confId":config_id,"crawlId":crawl_id, "type": "GENERATE"}
    generate = {
        "args": {
          "normalize": False,
          "filter": True,
          "crawlId" : "sample-crawl-01",
          "curTime": 1428526896161,
          "batch" : "1428526896161-4430"
        },
        "confId": "1c71cd51-b19c-4963-980e-6eb688c54b46",
        "crawlId": "sample-crawl-01",
        "type": "GENERATE"
    }

    resp_generate = requests.post(NUTCH_URL + '/job/create', json=generate)

    #fetch = {"args": {"threads": 50, "crawlId" : crawl_id, "batch" : batch},"confId":config_id,"crawlId":crawl_id ,"type": "FETCH"}
    fetch = {
    "args": {
      "threads": 50,
      "crawlId" : "sample-crawl-01",
      "batch" : "1428526896161-4430"
    },
    "confId": "1c71cd51-b19c-4963-980e-6eb688c54b46",
    "crawlId": "sample-crawl-01",
    "type": "FETCH"
}

    resp_fetch = requests.post(NUTCH_URL + '/job/create', json=fetch)

    #parse = {"args": {"crawlId" : crawl_id, "batch" : batch}, "confId":config_id,"crawlId":crawl_id ,"type": "PARSE"}
    parse = {
    "args": {
      "crawlId" : "sample-crawl-01",
      "batch" : "1428526896161-4430"
    },
    "confId": "1c71cd51-b19c-4963-980e-6eb688c54b46",
    "crawlId": "sample-crawl-01",
    "type": "PARSE"
}

    resp_parse = requests.post(NUTCH_URL + '/job/create', json=parse)

    #updatedb = {"args": {"crawlId" : crawl_id, "batch" : batch },"confId":config_id, "crawlId":crawl_id ,"type": "UPDATEDB"}
    updatedb = {
    "args": {
      "crawlId" : "sample-crawl-01",
      "batch" : "1428526896161-4430"
    },
    "confId": "1c71cd51-b19c-4963-980e-6eb688c54b46",
    "crawlId": "sample-crawl-01",
    "type": "UPDATEDB"
}

    resp_updatedb = requests.post(NUTCH_URL+'/job/create', json=updatedb)