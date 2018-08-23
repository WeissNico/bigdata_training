import elasticsearch as es


class Elastic():
    es = None

    def __init__(self):
        self.es = es.Elasticsearch(
            host=("portal-ssl223-11.bmix-lon-yp-2012af18-4749-4d32-94a6-"
                  "09573ff5ee35.3259324498.composedb.com"),
            port=26611,
            http_auth=('admin', 'RYZUAYORFMEGJRCT'),
            use_ssl=True,
            timeout=60)

    def insert_document(self, doc, doc_id, index="eurlex", doc_type="nutch"):
        """Inserts a document into the index `index` under `doc_id`

        Args:
            doc (dict): the document to insert.
            doc_id (str): the document id.
            index (str): an elasticsearch index, defaults to "eurlex".
            doc_type (str): an elasticsearch doc_type, defaults to "nutch".

        Returns:
            es.Response: the response object of elastic search
        """
        res = self.es.index(index=index, doc_type=doc_type, id=doc_id,
                            body=doc)
        return res

    def exist_document(self, base_url, doc_hash, index="eurlex"):
        """Checks whether a document for the given features exists.

        It compares `base_url` and the documents `doc_hash`.

        Args:
            base_url (str): the document's 'baseUrl'.
            doc_hash (str): the document's sha256-hash.
            index (str): an elastic search index, defaults to "eurlex".

        Returns:
            bool: whether the document exists or not
        """
        query = {"query": {
                    "bool": {
                        "should": [
                           {"match": {"baseUrl.keyword": base_url}},
                           {"match": {"hash.keyword": doc_hash}}
                        ]
                    }},
                 "_source": ["baseUrl", "hash", "version"]}
        result = self.es.search(index=index, body=query)
        return result['hits']['total'] > 0
