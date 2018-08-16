import requests
import elasticsearch
from elasticsearch import Elasticsearch, RequestsHttpConnection
import datetime

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
        res = self.es.index(index="eurlex", doc_type='nutch', id=doc_id, body=doc)

        return res


    def exist_document(self, baseUrl, hash):
        result = self.es.search(index="eurlex", body={"query": {"bool": {"should": [{"match": {"baseUrl.keyword": baseUrl}},{"match": {"hash.keyword": hash}}]}}, "_source": ["baseUrl", "hash", "version"]})
        return result['hits']['total']

