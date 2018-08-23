# -*- coding: utf-8 -*-
"""
Created on Thu May 17 09:12:48 2018

@author: j.ischebeck
"""

import requests
import time
import logging
from random import randint
import json
NUTCH_URL = 'http://159.122.175.139:30081'


class ApiError:
    def __init__(self, error):
        self.error = error


def _getJobStatus(jobid, seedDir, config):
    resp_status = requests.get(NUTCH_URL + '/job/' + jobid)
    status_json = json.loads(resp_status.text)
    status_msg = status_json['state']
    return status_msg


def _pollStatus(response, seedDir, config):
    if response.status_code != (201 and 200):
        raise ApiError(f"POST /job/create/ {response.status_code}")
    # poll for results
    while _getJobStatus(response.text, seedDir, config) != "FINISHED":
        time.sleep(1)
    return


def crawlerSites(seedList, collectionId, counter=1):
    test_id = "12348"
    status = 1

    list = []
    for idx, url in enumerate(seedList):
        list.append({"id": idx, "seedList": None, "url": url})

    # seed parameters
    seed = {"id": test_id, "name": "mynutch", "seedUrls": list}

    resp = requests.post(NUTCH_URL + '/seed/create', json=seed)
    if resp.status_code != (201 and 200):
        raise ApiError(f"POST /seed/create/ {resp.status_code}")

    logging.info(f"Created Seed. ID: {resp.text}")

    seedDir = resp.text
    # i.e. "/tmp/1526547667623-0"  # comes from first request  1526463295128-0
    crawl_id = collectionId

    # inject
    job_def = {"args": {"seedDir": seedDir}, "confId": "default",
               "crawlId": crawl_id, "type": "INJECT"}

    resp = requests.post(NUTCH_URL + '/job/create', json=job_def)
    if resp.status_code != (201 and 200):
        raise ApiError('POST /job/create/ {}'.format(resp.status_code))

    logging.info("Created Job data: {}".format(resp.text))

    config = "default"  # resp_config.text #"default"

    for run in range(counter):
        logging.info(f"--- Run {run} ---")
        time1 = int(round(time.time()*1000))
        batch = str(time1) + "-" + str(randint(1000, 9999))
        logging.info(f"Starting time: {time1}.")
        # generate parameters
        generate = {"args": {"normalize": False, "filter": True,
                             "crawlId": crawl_id, "curTime": time1,
                             "batch": batch},
                    "confId": config, "crawlId": crawl_id, "type": "GENERATE"}
        resp_generate = requests.post(NUTCH_URL + '/job/create', json=generate)
        _pollStatus(resp_generate, seedDir, config)
        logging.info("NUTCH GENERATE successful!")

        # fetch parameters
        fetch = {"args": {"threads": 50, "crawlId": crawl_id,
                          "batch": batch},
                 "confId": config, "crawlId": crawl_id, "type": "FETCH"}
        resp_fetch = requests.post(NUTCH_URL + '/job/create', json=fetch)
        _pollStatus(resp_fetch, seedDir, config)
        logging.info("NUTCH FETCH successful!")

        # parse parameters
        parse = {"args": {"crawlId": crawl_id, "batch": batch},
                 "confId": config, "crawlId": crawl_id, "type": "PARSE"}
        resp_parse = requests.post(NUTCH_URL + '/job/create', json=parse)
        _pollStatus(resp_parse, seedDir, config)
        logging.info("NUTCH PARSE successful!")

        # updatedb parameters
        updatedb = {"args": {"crawlId": crawl_id, "batch": batch},
                    "confId": config, "crawlId": crawl_id, "type": "UPDATEDB"}
        resp_updatedb = requests.post(NUTCH_URL+'/job/create', json=updatedb)
        _pollStatus(resp_updatedb, seedDir, config)
        logging.info("NUTCH UPDATEDB successful!")
        logging.info(f"--- Run {run} finished ---")

    return status
