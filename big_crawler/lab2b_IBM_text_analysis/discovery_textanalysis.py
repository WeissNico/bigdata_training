# -*- coding: utf-8 -*-
"""

Textanalysis (default settings + keywords) of files using Discovery

Save result of the analysis to JSON

"""

import json
import os
import watson_developer_cloud
import sys
from watson_developer_cloud import DiscoveryV1

#%%
discovery = watson_developer_cloud.DiscoveryV1(
    '2016-11-07',
    username='68aa6cc2-6ac7-493f-8989-9f71a3b1a3c8',
    password='NFjvZItut5Vu',
    url= "https://gateway-fra.watsonplatform.net/discovery/api")



news_environment_id = '3e870668-3533-43ec-8cca-b4e2d203b348'
collectionid = '7dfb56cb-87ae-4c8f-8bf9-03cbfb5da9b4'

print(json.dumps(news_environment_id, indent=2))



configurations_id = 'ed56e1a8-7f94-40c1-aebe-08e789389599'    # Configuration: NLU with the additional enrichment for keywords

configurations = discovery.get_configuration(news_environment_id,configurations_id)


print(json.dumps(configurations_id, indent=2))

print(json.dumps(configurations, indent=2))

filename = 'f'


# query for general analysis of all files
# to generate list of entities, concepts and keywords which can be used for tagging
my_query = discovery.query(environment_id=news_environment_id, collection_id=collectionid)


#more general query for search queries
# full-text search and filter options

#my_query = discovery.query(environment_id='{environment_id}', collection_id='{collection_id}', query='{query}', filter='{filter}', aggregation='{aggregation}', return_fields='{return_fields}'

str_my_query = str(my_query).encode("utf-8")


print(json.dumps(my_query, indent=2))
#print('Filename:', filename, file=print(json.dumps(my_query, indent=2)))  # Python 3.x


sys.stdout=open("test.txt","w")
print ("hello",'my_query')
sys.stdout.close()


print(str_my_query, file=open('results.json', 'w'))

