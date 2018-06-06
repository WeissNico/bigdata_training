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



#config_delete = discovery.delete_configuration(news_environment_id, '9de79ec7-9396-412a-abd7-673cbddf54fa')


configs = discovery.list_configurations(news_environment_id)
print(json.dumps(configs, indent=2))


configurations_id = 'ed56e1a8-7f94-40c1-aebe-08e789389599'

configurations = discovery.get_configuration(news_environment_id,configurations_id)

#configurations_id = 'cb42c1fb-5474-496b-9fae-25582d296fe7'

print(json.dumps(configurations_id, indent=2))

print(json.dumps(configurations, indent=2))



#data = {
#  "configuration_id" : "53bcfa98-886e-4067-a66f-70bcfdd3c86e",
#  "name" : "IBM News",
#  "created" : "2015-08-24T18:42:25.324Z",
#  "updated" : "2015-08-24T18:42:25.324Z",
#  "description" : "A configuration useful for ingesting IBM press releases.",
#  "conversation": [],
#  "enrichments" : [],
#  "normalizations" : []
#}


#enrich = [{'source_field': 'text', 'destination_field': 'enriched_text', 'enrichment': 'natural_language_understanding', 'options': {'features': {'entities': {'sentiment': True, 'emotion': False, 'limit': 50}, 'sentiment': {'document': True}, 'categories': {}, 'concepts': {'limit': 8}}}}]

#new_config = discovery.create_configuration(news_environment_id, 'NLU_test0606_1', 'change_enrichment', data['conversation'],enrich, data['normalizations'])


#print(json.dumps(new_config, indent=2))




collections = discovery.list_collections(news_environment_id)
news_collections = [x for x in collections['collections']]
print(json.dumps(news_collections, indent=2))


#configurations = discovery.list_configurations(
#    environment_id=news_environment_id)
#print(json.dumps(configurations, indent=2))


query_options = {'query': 'IBM'}
query_results = discovery.query(news_environment_id,
                                news_collections[0]['collection_id'],
                                query_options)

news_collection_id = news_collections[0]['collection_id']            # AKTUELLER TEST !!!!!
print(json.dumps(query_results, indent=2))









if (discovery.get_environment(environment_id=news_environment_id)['status'] == 'active'):
    writable_environment_id = news_environment_id

#    new_collection = discovery.create_collection(environment_id=writable_environment_id,
#                                                 name='Reports',
#                                                 description="Reports English Data")

    new_collection =discovery.create_collection(environment_id=writable_environment_id, configuration_id=configurations_id,
                                name = 'Reports', description="Reports English Data")


    print(new_collection)

    with open(os.path.join(os.getcwd(), 'Reports', 'AkamaiFileDownload.pdf'), "rb") as fileinfo:
        add_doc = discovery.add_document(environment_id=writable_environment_id,
                                     collection_id=new_collection['collection_id'], file=fileinfo)
        print(json.dumps(add_doc, indent=2))

