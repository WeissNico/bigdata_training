"""This module holds `Elastic` a class for connecting to an ES-database.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import logging
import re

import elasticsearch as es

import elastic_sortkeys as esort


class _EasyAccess():
    """Provides a way to access a dict, by using attributes as key.

    If the attribute can not be found, it returns `None`."""
    def __init__(self, a_dict):
        self.dict = a_dict

    def __getattr__(self, name):
        # skip internal values event when they're present in the dict.
        return self.dict.get(name, None)


class Elastic():
    DOC_MAPPING = {
        "properties": {
            "hash": {"type": "keyword"},
            "version": {"type": "double"},
            "document": {"type": "keyword"},
            "date": {"type": "date"},
            "source": {"type": "keyword"},
            "text": {"type": "text"},
            "content_type": {"type": "keyword"},
            "content": {"type": "binary"},
            "tags": {"type": "keyword"},
            "quantity": {
                "properties": {
                    "lines": {"type": "integer"},
                    "words": {"type": "integer"}
                }
            },
            "change": {
                "properties": {
                    "lines_added": {"type": "integer"},
                    "lines_removed": {"type": "integer"}
                }
            },
            "keywords": {
                "properties": {
                    "*": {"type": "half_float"}
                },
            },
            "entities": {
                "properties": {
                    "*": {"type": "half_float"}
                },
            },
            "metadata": {"type": "object", "dynamic": True},
            "status": {"type": "byte"},
            "impact": {"type": "byte"},
            "type": {"type": "keyword"},
            "category": {"type": "keyword"},
            "fingerprint": {"type": "keyword"},
            "new": {"type": "boolean"}  # False for modified values
        }
    }

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
            "doc_type": "nutch",
            "size": 10
        }
        self._default_wrapper = _EasyAccess(self.defaults)

        self.defaults.update(kwargs)

        self.es = es.Elasticsearch(host=host, port=port, http_auth=auth,
                                   use_ssl=True, timeout=60)

        # check whether the document index exists, if not create it.
        if not self.es.indices.exists(index=self._dflt.docs_index):
            self.es.indices.create(index=self._dflt.docs_index)
            # put the mapping into the docs index
            self.es.indices.put_mapping(doc_type=self._dflt.doc_type,
                                        index=self._dflt.docs_index,
                                        body=self.DOC_MAPPING)

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

    def exist_document(self, source, doc_hash):
        """Checks whether a document for the given features exists.

        It compares `source` and the documents `doc_hash`.

        Args:
            source (str): the document's 'baseUrl'.
            doc_hash (str): the document's sha256-hash.

        Returns:
            bool: whether the document exists or not
        """
        query = {"query": {
                    "bool": {
                        "should": [
                           {"match": {"source": source}},
                           {"match": {"hash": doc_hash}}
                        ]
                    }},
                 "_source": ["source", "hash", "version"]}
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
        self.es.update(index=index, doc_type=doc_type, id=doc_id, body=doc)

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

    def search_documents(self, search_text, page=1, filters={}, sort_by=None):
        """Returns all documents, that contain the `search_text`.

        The results can be filtered by the filters defined in the `filters`
        dict. It assumes an OR connection for multiple values.

        Args:
            search_text (str): the text to search for.
            filters (dict): the filters for fields of the documents.
            sortby (dict): accepts a dict with the keys `keyword`, `order` and
                `args`.

        Returns:
            list: a list of documents, as returned by elasticsearch.
        """
        index = self._dflt.docs_index
        logging.debug(f"Searching for {search_text} on '{index}'")

        start = (page - 1) * self._dflt.size
        search = {"simple_query_string": {"query": search_text}}
        # if search_text is empty or None
        if not search_text:
            search = {"match_all": {}}

        s_body = {
            "from": start,
            "size": self._dflt.size,
            "query": {
                "bool": {
                    "must": search,
                    "filter": _transform_filters(filters)
                }
            },
            "sort": esort.transform_sortby(sort_by),
            "highlight": {
                "fields": {
                    "*": {
                        "pre_tags": ["<b>"],
                        "post_tags": ["</b>"]
                    }
                }
            }
        }
        results = self.es.search(index=index, body=s_body,
                                 filter_path="hits.hits._source")
        return results


def _transform_filters(filters):
    """Transforms a given dict of filters into an elastic filter context."""
    filter_context = []

    for key in filters.keys():
        cur_context = {}
        # check whether this is a range key
        match = re.match(r"(.+)_(from|to)$", key)
        # skip "to" keys
        if match and match[2] == "from":
            cur_context = {
                "range": {
                    match[1]: {
                        "gte": filters[key],
                        "lte": filters[f"{match[1]}_to"]
                    }
                }
            }
        else:
            keyword = "term"
            if isinstance(filters[key], list):
                keyword = "terms"
            cur_context = {
                keyword: {key: filters[key]}
            }
        filter_context.append(cur_context)
    return filter_context
