# -*- coding: utf-8 -*-
"""

"""

import json
import os
import watson_developer_cloud
from watson_developer_cloud import DiscoveryV1

#%%
discovery = watson_developer_cloud.DiscoveryV1(
    '2016-11-07',
    username='68aa6cc2-6ac7-493f-8989-9f71a3b1a3c8',
    password='NFjvZItut5Vu',
    url= "https://gateway-fra.watsonplatform.net/discovery/api")


environments = discovery.list_environments()
print(json.dumps(environments, indent=2))

news_environments = [x for x in environments['environments'] if x['name'] == 'Anacredit']
news_environment_id = news_environments[0]['environment_id']
print(json.dumps(news_environment_id, indent=2))

collections = discovery.list_collections(news_environment_id)
news_collections = [x for x in collections['collections']]
print(json.dumps(news_collections, indent=2))

configurations = discovery.list_configurations(
    environment_id=news_environment_id)
print(json.dumps(configurations, indent=2))


query_options = {'query': 'IBM'}
query_results = discovery.query(news_environment_id,
                                news_collections[0]['collection_id'],
                                query_options)

news_collection_id = news_collections[0]['collection_id']            # AKTUELLER TEST !!!!!
print(json.dumps(query_results, indent=2))

if (discovery.get_environment(environment_id=news_environment_id)['status'] == 'active'):
    writable_environment_id = news_environment_id

    new_collection = discovery.create_collection(environment_id=writable_environment_id,
                                                 name='Reports',
                                                 description="Reports English Data")

    print(new_collection)

    with open(os.path.join(os.getcwd(), 'Reports', 'AkamaiFileDownload.pdf')) as fileinfo:
        add_doc = discovery.add_document(environment_id=writable_environment_id,
                                     collection_id=new_collection['collection_id'], file=fileinfo)
        print(json.dumps(add_doc, indent=2))

