# -*- coding: utf-8 -*-
"""
Created on Wed Nov  1 17:26:50 2017

@author: j.ischebeck
"""

import json
import os
import watson_developer_cloud

#%%
discovery = watson_developer_cloud.DiscoveryV1(
    '2016-11-07',
    username='68aa6cc2-6ac7-493f-8989-9f71a3b1a3c8',
    password='NFjvZItut5Vu',
    url= "https://gateway-fra.watsonplatform.net/discovery/api")

#%%
environments = discovery.get_environments()
print(json.dumps(environments, indent=2))
#%%
news_environments = [x for x in environments['environments'] if
                     x['name'] == 'Watson News Environment']
news_environment_id = news_environments[0]['environment_id']
print(json.dumps(news_environment_id, indent=2))

#%%
collections = discovery.list_collections(news_environment_id)
news_collections = [x for x in collections['collections']]
print(json.dumps(collections, indent=2))

configurations = discovery.list_configurations(
    environment_id=news_environment_id)
print(json.dumps(configurations, indent=2))

query_options = {'query': 'IBM'}
query_results = discovery.query(news_environment_id,
                                news_collections[0]['collection_id'],
                                query_options)
print(json.dumps(query_results, indent=2))

#%%
new_environment = discovery.create_environment(name="Anacredit", description="Anacredit Environment")
print(new_environment)

#%%

if (discovery.get_environment(environment_id=new_environment['environment_id'])['status'] == 'active'):
   writable_environment_id = new_environment['environment_id']
   
   new_collection = discovery.create_collection(environment_id=writable_environment_id,
                                                name='Anacredit Collection',
                                                description="Anacredit English Data")

   print(new_collection)

#%%   
if 1==2:
   print(discovery.list_collections(environment_id=writable_environment_id))
   #res = discovery.delete_collection(environment_id='10b733d0-1232-4924-a670-e6ffaed2e641',
   #                                  collection_id=new_collection['collection_id'])

#    print(res)

# collections = discovery.list_collections(environment_id=writable_environment_id)
# print(collections)
#%%
#os.chcwd('D:\dev\faq_bot')
print (os.path.join(os.getcwd(),'Anacredit','anacredit_faq.pdf'))

#%%

with open(os.path.join(os.getcwd(),'Anacredit','anacredit_faq.pdf')) as fileinfo:
    print(discovery.test_document(environment_id=writable_environment_id, fileinfo=fileinfo))

#%%
with open(os.path.join(os.getcwd(),'Anacredit','anacredit_faq.pdf')) as fileinfo:
    print(discovery.add_document(environment_id=writable_environment_id, collection_id= new_collection['collection_id'], file_info=fileinfo, mime_type='application/x-pdf'))

# In[25]:

# with open(os.path.join(os.getcwd(),'..','resources','simple.html')) as fileinfo:
#     res = discovery.add_document(environment_id=writable_environment_id,
#                                 collection_id=collections['collections'][0]['collection_id'],
#                                 fileinfo=fileinfo)
#    print(res)


#res = discovery.get_collection(environment_id=writable_environment_id,
#                               collection_id=collections['collections'][0]['collection_id'])
#print(res['document_counts'])


#res = discovery.delete_environment(environment_id=writable_environment_id)
#print(res)