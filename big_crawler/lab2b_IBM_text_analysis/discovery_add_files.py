# -*- coding: utf-8 -*-
"""

Upload files to an existing collection in Discovery.
Here: All files from a specific directory

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



news_environment_id = '3e870668-3533-43ec-8cca-b4e2d203b348'
collectionid = '7dfb56cb-87ae-4c8f-8bf9-03cbfb5da9b4'

print(json.dumps(news_environment_id, indent=2))



#config_delete = discovery.delete_configuration(news_environment_id, '9de79ec7-9396-412a-abd7-673cbddf54fa')




configurations_id = 'ed56e1a8-7f94-40c1-aebe-08e789389599'    # Configuration: NLU with the additional enrichment for keywords

configurations = discovery.get_configuration(news_environment_id,configurations_id)


print(json.dumps(configurations_id, indent=2))

print(json.dumps(configurations, indent=2))

#delete_doc = discovery.delete_document(environment_id=news_environment_id, collection_id=collectionid, '{document_id}')
#print(json.dumps(delete_doc, indent=2))


import glob

files = glob.glob("C:\\Users\\an.kaiser\Downloads\\bigdata_training-master\\bigdata_training\\big_crawler\\lab2b_IBM_text_analysis\\Reports\\*.pdf")
print(files[1])

ii = len(files)

print(ii)

if (discovery.get_environment(environment_id=news_environment_id)['status'] == 'active'):
    writable_environment_id = news_environment_id

for i in range(0, ii):

    str_filename=str(files[i])
    n = 114
    str1_filename = str_filename[n:]
    print(str_filename)
    print(str1_filename)
    i=i+1
    with open(os.path.join(os.getcwd(), 'Reports', str1_filename), "rb") as fileinfo:
        add_doc = discovery.add_document(environment_id=writable_environment_id,
                                     collection_id=collectionid, file=fileinfo)
        print(json.dumps(add_doc, indent=2))