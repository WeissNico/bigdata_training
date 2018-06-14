import requests
import elasticsearch
from elasticsearch import Elasticsearch, RequestsHttpConnection
import datetime
import traceback
#print(es1.info())

class Elastic():

    es = None
    def __init__(self):
        self.es = Elasticsearch(
            host='portal-ssl223-11.bmix-lon-yp-2012af18-4749-4d32-94a6-09573ff5ee35.3259324498.composedb.com',
            port=26611,
            http_auth=('admin', 'RYZUAYORFMEGJRCT'),
            use_ssl=True,
            timeout=60)

    def insert_dokument(self, doc, doc_id):
        #doc = {
        #    'author': 'kimchy',
        #    'text': 'Elasticsearch: cool. bonsai cool.',
        #    'timestamp': datetime.now(),
        #}
        res = self.es.index(index="testcase", doc_type='nutch', id=doc_id, body=doc)

        return res

    def remove_tag(self, tag, doc_id):


        document = self.es.get(index="testcase", doc_type='nutch', id=doc_id)

        tags_list = document['_source']['tags']
        tags_list.remove(tag)

        doc = {
            "script": "ctx._source.remove('tags')"
        }
        self.es.update(index="testcase", doc_type='nutch', id=doc_id, body=doc)

        doc = {
            "script": "ctx._source.tags = []"
        }
        self.es.update(index="testcase", doc_type='nutch', id=doc_id, body=doc)

        for tag in tags_list:
            self.update_tag(tag, doc_id)

        #self.es.indices.refresh(index="testcase")

    def update_tag(self, tag, doc_id):
        doc = {
            "script": {
                "inline": "ctx._source.tags.add(params.tag)",
                "params": {
                    "tag": tag
                }
            }
        }

        self.es.update(index="testcase", doc_type='nutch', id=doc_id, body=doc)
        self.es.indices.refresh(index="testcase")


    def get_seeds(self):
        try:
            res = self.es.search(index="seeds", body={"query": {"match_all": {}}})

            newlist = {}
            for k, value in enumerate(res['hits']['hits']):
                category = value['_source']['category']
                val = {'id': value['_id'], 'category': category , 'name': value['_source']['name'], 'url': value['_source']['url']}
                if  value['_source']['category'] not in newlist:
                    newlist[category] = []
                newlist[category].append(val)

        except Exception as e:
            print(traceback.format_exc())
            res = []
        return newlist

    def set_seed(self, seed):
        doc = {
            "url":seed['url'],
            "category":seed['category'],
            "name":seed['name']
        }

        doc_id = seed['doc_id']

        result = self.es.index(index="seeds", doc_type='nutch', id=doc_id, body=doc)
        return result

    def delete_seed(self, doc_id):

        result = self.es.delete(index="seeds", doc_type="nutch", id=doc_id)
        return result






#res = es1.indices.delete(index='test', ignore=[400, 404])
