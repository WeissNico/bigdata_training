"""This module holds `Elastic` a class for connecting to an ES-database.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import logging

import elasticsearch as es

import elastic_transforms as etrans


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
            "source": {
                "properties": {
                    "url": {"type": "keyword"},
                    "name": {"type": "keyword"},
                }
            },
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
            "status": {"type": "keyword"},
            "impact": {"type": "keyword"},
            "type": {"type": "keyword"},
            "category": {"type": "keyword"},
            "fingerprint": {"type": "keyword"},
            "version_key": {"type": "keyword"},
            "connections": {
                "type": "object",
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "similarity": {"type": "float"}
                }
            },
            "new": {"type": "boolean"}  # False for modified values
        }
    }

    SCRIPTS = {
        "keyword_sort": {
            "script": {
                "lang": "painless",
                "source": """
                    String field = params.getOrDefault("_field", "hash");
                    def val = doc[field];
                    return params.getOrDefault(val, 0);
                """
            }
        },
        "reading_time": {
            "script": {
                "lang": "painless",
                "source": """
                    int time = (int) ((doc['quantity.words'].value * 0.4 *
                               params.getOrDefault(doc['type'].value, 1.0))
                               /60);
                    return time;
                """
            },
            "type": "integer"
        },
        "reading_time_range": {
            "script": {
                "lang": "painless",
                "source": """
                    int from = params.getOrDefault("gte", 0);
                    int to = params.getOrDefault("lte", Integer.MAX_VALUE);
                    int time = (int) ((doc['quantity.words'].value * 0.4 *
                               params.getOrDefault(doc['type'].value, 1.0))
                               /60);
                    return (from <= time) && (time <= to);
                """
            },
            "type": "integer"
        },
        "similarity": {
            "script": {
                "lang": "painless",
                "source": ("doc['fingerprint'].value - params.fingerprint"),
            }
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

        for script_id, script_body in self.SCRIPTS.items():
            self.es.put_script(id=script_id, body=script_body)

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

    def get_query_filters(self, search_text, fields=None, active=None):
        """Returns all possible filters for the documents containing the query.

        Args:
            search_text (str): the text to search for.
            fields (list): a list of fields that should be aggregated.
                Defaults to None, which means all fields.
            active (dict): the filter dict as returned to the normal search.

        Returns:
            dict: a dictionary of aggregations.
        """
        index = self._dflt.docs_index
        logging.debug(f"Searching for {search_text} on '{index}'")

        search = {
            "simple_query_string": {
                "query": search_text,
                "default_operator": "and"
            }
        }
        # if search_text is empty or None
        if not search_text:
            search = {"match_all": {}}

        s_body = {
            "query": {
                "bool": {
                    "must": search,
                }
            },
            "aggs": etrans.transform_aggs(fields),
        }
        # inserts the fields, if necessary.
        source, scripted = etrans.transform_fields(fields)
        if source is not None:
            s_body["_source"] = source
        if scripted is not None:
            s_body["script_fields"] = scripted

        results = self.es.search(index=index, body=s_body)

        return etrans.transform_agg_filters(results["aggregations"], active)

    def search_documents(self, search_text, page=1, fields=None, filters={},
                         sort_by=None, highlight=True):
        """Returns all documents, that contain the `search_text`.

        The results can be filtered by the filters defined in the `filters`
        dict. It assumes an OR connection for multiple values.

        Args:
            search_text (str): the text to search for.
            page (int): the page of the results that should be shown.
            fields (list): a list of fields that should be returned.
                Defaults to None, which means all fields.
            filters (dict): the filters for fields of the documents.
            sortby (dict): accepts a dict with the keys `keyword`, `order` and
                `args`.
            highlight (boolean): Whether text highlights for the query should
                be done.

        Returns:
            dict: a dictionary containing the following keys:
                `num_results`, `total_pages` and `results`.
        """
        index = self._dflt.docs_index
        logging.debug(f"Searching for {search_text} on '{index}'")

        start = (page - 1) * self._dflt.size
        search = {
            "simple_query_string": {
                "query": search_text,
                "default_operator": "and"
            }
        }
        # if search_text is empty or None
        if not search_text:
            search = {"match_all": {}}

        highlighter = {}
        if highlight:
            highlighter = {"fields": {"*": {"pre_tags": ["<b>"],
                                            "post_tags": ["</b>"]}}}

        s_body = {
            "from": start,
            "size": self._dflt.size,
            "query": {
                "bool": {
                    "must": search,
                    "filter": etrans.transform_filters(filters)
                }
            },
            "sort": etrans.transform_sortby(sort_by),
            "highlight": highlighter,
            "aggs": etrans.transform_aggs(fields),
        }
        # inserts the fields, if necessary.
        source, scripted = etrans.transform_fields(fields)
        if source is not None:
            s_body["_source"] = source
        if scripted is not None:
            s_body["script_fields"] = scripted

        results = self.es.search(index=index, body=s_body)
        # add the id to the results
        for doc in results["hits"]["hits"]:
            # insert the id into the source (which will be returned)
            doc["_source"]["_id"] = doc["_id"]
            # insert all (scripted_)fields into the source
            doc["_source"].update(doc.get("fields", {}))

        docs = [doc["_source"] for doc in results["hits"]["hits"]]

        total_pages, rem = divmod(results["hits"]["total"], self._dflt.size)
        if rem > 0:
            total_pages += 1

        return {
            "num_results": results["hits"]["total"],
            "total_pages": total_pages,
            "results": docs,
            "aggs": etrans.transform_agg_filters(results.get("aggregations"))
        }
