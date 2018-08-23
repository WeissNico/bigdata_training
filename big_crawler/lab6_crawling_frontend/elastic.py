"""This module holds `Elastic` a class for connecting to an ES-database.

Additionally, there are utility-function aiming specifically for the
transformation of documents.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import elasticsearch as es
import logging

import utility as ut


class _EasyAccess():
    """Provides a way to access a dict, by using attributes as key.

    If the attribute can not be found, it returns `None`."""
    def __init__(self, a_dict):
        self.dict = a_dict

    def __getattr__(self, name):
        # skip internal values event when they're present in the dict.
        return self.dict.get(name, None)


class Elastic():
    def __init__(self, host="localhost", port=9000, auth=None, **kwargs):
        """Initialize the elasticsearch client.

        Args:
            host (str): the host of the elasticsearch database.
                Defaults to `'localhost'`.
            port (int): the port of the elasticsearch database.
                Defaults to `9000`.
            auth (tuple): a tuple of username and password, defaults to `None`.
            **kwargs (dict): keyword arguments that updates the defaults.

        Returns:
            Elastic: a new elasticsearch client.
        """
        self.defaults = {
            "seeds_index": "seeds",
            "docs_index": "eurlex",
            "doc_type": "nutch"
        }
        self._default_wrapper = _EasyAccess(self.defaults)

        self.defaults.update(kwargs)

        self.es = es.Elasticsearch(
            host=host,
            port=port,
            http_auth=auth,
            use_ssl=True,
            timeout=60)

    @property
    def _dflt(self):
        """Convenience property to retrieve the default values.

        Returns:
            _EasyAccess: an easy access wrapper around the default dict.
        """
        return self._default_wrapper

    def insert_document(self, doc, doc_id):
        """Inserts a document into the index `index` under `doc_id`

        Args:
            doc (dict): the document to insert.
            doc_id (str): the document id.

        Returns:
            es.Response: the response object of elastic search
        """
        res = self.es.index(index=self._dflt.docs_index,
                            doc_type=self._dflt.doc_type,
                            id=doc_id, body=doc)
        return res

    def exist_document(self, base_url, doc_hash):
        """Checks whether a document for the given features exists.

        It compares `base_url` and the documents `doc_hash`.

        Args:
            base_url (str): the document's 'baseUrl'.
            doc_hash (str): the document's sha256-hash.
            index (str): an elastic search index, defaults to None.

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
        result = self.es.search(index=self._dflt.docs_index, body=query)
        return result['hits']['total'] > 0

    def remove_tag(self, tag, doc_id):
        """Removes tag `tag` from document `doc_id`.

        Args:
            tag (str): the tag to remove.
            doc_id (str): the document id.
        """
        index = self._dflt.docs_index
        doc_type = self._dflt.doc_type

        document = self.es.get(index=index, doc_type=doc_type, id=doc_id)

        tags_list = document['_source']['tags']
        tags_list.remove(tag)

        doc = {
            "script": "ctx._source.remove('tags')"
        }
        self.es.update(inex=index, doc_type=doc_type, id=doc_id, body=doc)

        doc = {
            "script": "ctx._source.tags = []"
        }
        self.es.update(index=index, doc_type=doc_type, id=doc_id, body=doc)

        for tag in tags_list:
            self.update_tag(tag, doc_id)

    def update_tag(self, tag, doc_id):
        """Adds tag `tag` to document `doc_id`.

        Args:
            tag (str): the tag to remove.
            doc_id (str): the document id.
        """
        index = self._dflt.docs_index
        doc_type = self._dflt.doc_type

        doc = {
            "script": {
                "inline": "ctx._source.tags.add(params.tag)",
                "params": {
                    "tag": tag
                }
            }
        }

        self.es.update(index=index, doc_type=doc_type, id=doc_id, body=doc)
        self.es.indices.refresh(index=index)

    def get_seeds(self):
        """Returns the seeds.

        Returns:
            list: a list of document seedds.
        """
        index = self._dflt.seeds_index

        try:
            res = self.es.search(index=index,
                                 body={"query": {"match_all": {}}})
            newlist = {}
            for k, value in enumerate(res['hits']['hits']):
                category = value['_source']['category']
                val = {'id': value['_id'],
                       'category': category,
                       'name': value['_source']['name'],
                       'url': value['_source']['url']}
                if value['_source']['category'] not in newlist:
                    newlist[category] = []
                newlist[category].append(val)
        except Exception as e:
            logging.error(f"An error occured while retrieving the seeds. {e}")

        return newlist

    def set_seed(self, seed):
        """Adds a new seed to the database.

        Args:
            seed (dict): a dict containing the keys `url`, `name` and
                `category`.

        Returns:
            `elasticsearch.Response`: the response of the es database.
        """
        index = self._dflt.seeds_index
        doc_type = self._dflt.doc_type

        doc = {k: seed.get(k) for k in ["url", "name", "category"]}
        doc_id = seed['doc_id']

        result = self.es.index(index=index, doc_type=doc_type, id=doc_id,
                               body=doc)
        return result

    def delete_seed(self, seed_id):
        """Removes a seed from the database.

        Args:
            seed_id (str): the id of the seed

        Returns:
            `elasticsearch.Response`: the response of the es database.
        """
        index = self._dflt.seeds_index
        doc_type = self._dflt.doc_type

        result = self.es.delete(index=index, doc_type=doc_type, id=seed_id)
        return result

    def search_documents(self, search_text):
        """Returns all documents, that contain the `search_text`.

        Args:
            search_text (str): the text to search for.

        Returns:
            list: a list of documents, as returned by elasticsearch.
        """
        index = self._dflt.docs_index
        logging.debug(f"Searching for {search_text} on '{index}'")
        s_body = {
            "query": {
                "simple_query_string": {
                    "query": search_text
                }
            },
            "highlight": {"fields": {"*": {"pre_tags": ["<b>"],
                                           "post_tags": ["</b>"]}}}}
        results = self.es.search(index=index, body=s_body)

        data = [doc for doc in results['hits']['hits']]
        return data


def transform_doc(document, **kwargs):
    """Transforms a document into an easily retrievable dict-format.

    The (complete) format of a returned document is as follows:
    `{
        "id": "the document's id",
        "date": date(2018, 8, 21),
        "title": "the document's title",
        "source": "the document's source link",
        "text": ["the contained text", "..."],
        "tags": ["tag_1", "tag_2", "..."],
        # these need to be constructed in the db first TODO
        "quantity": {"words": 1234, "lines": 123},
        "keywords": {"keyword": range(0, 1), "...": "..."},
        "entities": {"entity": range(0, 1), "...": "..."},
        "status": "open, waiting or finished",
        "impact": "high, medium or low",
        "type": "the document's type, i.e. 'FAQ'",
        "category": "the document's category, i.e. 'Risk management'",
        # these need to be calculated taking into consideration the whole db
        "new": True  # False for modified values
    }`

    Args:
        document (dict): A document as found in the elasticsearch database.
        **kwargs (dict): additionaly parameters that should be set for the doc.

    Returns:
        dict: a dictionary in the specified format.
    """
    doc = ut.dict_construct(document, {
        "id": (["_id"], "no_id"),
        "date": (["_source", "metadata", "date"], None),
        "title": (["_source", "title"], "no title"),
        "source": (["_source", "baseUrl"], "#"),
        "text": (["_source", "text"], []),
        "tags": (["_source", "tags"], []),
    })

    # update keys, that are included in the kwargs
    doc.update(kwargs)

    return doc
