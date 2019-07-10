"""This module holds `Elastic` a class for connecting to an ES-database.

It manages all the query hassles for our usecases.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import logging
import time
import ssl
import os

import elasticsearch as es

import utility
import analyzers
from . import transforms as etrans
from . import filestore


logger = logging.getLogger(__name__)


# shortcut for safe_dict_access
sda = utility.safe_dict_access


class Elastic():
    SETTINGS = {
        "index": {
            "mapping.ignore_malformed": "true"
        }
    }

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
            "content": {"type": "keyword"},
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

    SEED_MAPPING = {
        "properties": {
            "url": {"type": "keyword"},
            "name": {"type": "keyword"},
            "description": {"type": "text"},
            "category": {"type": "keyword"}
        }
    }

    SEARCH_MAPPING = {
        "properties": {
            "name": {"type": "keyword"},
            "keywords": {"type": "keyword"},
            "time_periods": {
                "type": "object",
                "properties": {
                    "type": {"type": "keyword"},
                    "from": {"type": "date"},
                    "to": {"type": "date"}
                }
            },
            "file_types": {"type": "keyword"},
            "sources": {"type": "keyword"}
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
        },
        "update_body": {
            "script": {
                "lang": "painless",
                "source": """
                    for (k in params.body.keySet()) {
                        ctx._source[k] = params.body[k];
                    }
                """
            }
        }
    }

    def __init__(self, host="localhost", port=9000, auth=None, cert=None,
                 **kwargs):
        """Initialize the elasticsearch client.

        Args:
            host (str): the host of the elasticsearch database.
                Defaults to `'localhost'`.
            port (int): the port of the elasticsearch database.
                Defaults to `9000`.
            auth (tuple): a tuple of username and password, defaults to `None`.
            cert (path): a path to a self-signed certificate as used by
                ibmcloud.
            **kwargs (dict): keyword arguments that updates the defaults.

        Returns:
            Elastic: a new elasticsearch client.
        """
        self.defaults = utility.DefaultDict(dict({
            "seeds_index": "seeds",
            "search_index": "searches",
            "docs_index": "eurlex",
            "doc_type": "nutch",
            "seed_type": "seed",
            "search_type": "search",
            "size": 10
        }, **kwargs))

        context = None
        if cert:
            if not os.path.exists(cert):
                logger.error(f"Certificate file: {cert} does not exist!")
            else:
                context = ssl.create_default_context(cafile=cert)

        self.es = es.Elasticsearch(host=host, port=port, http_auth=auth,
                                   use_ssl=True, ssl_context=context,
                                   timeout=60)
        self.fs = filestore.FileStore(self.defaults.fs_dir(None))

        for script_id, script_body in self.SCRIPTS.items():
            self.es.put_script(id=script_id, body=script_body)

        # check whether the document index exists, if not create it.
        self._create_index(self.defaults.docs_index(),
                           self.defaults.doc_type(),
                           self.DOC_MAPPING)
        self._create_index(self.defaults.seeds_index(),
                           self.defaults.seed_type(),
                           self.SEED_MAPPING)
        self._create_index(self.defaults.search_index(),
                           self.defaults.search_type(),
                           self.SEARCH_MAPPING)
        self.es.indices.close(index=self.defaults.docs_index())
        self.es.indices.put_settings(index=self.defaults.docs_index(),
                                     body=self.SETTINGS)
        self.es.indices.open(index=self.defaults.docs_index())

    def _create_index(self, index, doc_type, mapping):
        """Checks whether an index is present, if not, creates it.

        Uses the mapping provided.

        Args:
            index (str): the index that should be used.
            doc_type (str): the doc_type for the mapping.
            mapping (dict): the elastic-mapping that should be used.
        """
        if not self.es.indices.exists(index=index):
            self.es.indices.create(index=index)
            # put the mapping into the docs index
            self.es.indices.put_mapping(index=index, doc_type=doc_type,
                                        body=mapping)

    def _prepare_document(self, doc):
        """Prepares a document for insertion by constructing features.

        This also saves the contents to filesystem.
        This also runs the analyzers.

        Args:
            doc (dict): the document to insert.
                Expects the keys `content` and `metadata`.

        Returns:
            tuple: the enriched document (dict) and a unique identifier (str)
        """
        raw_hash = self.fs.set(doc.get("raw_content", None))
        doc_hash = self.fs.set(doc.get("content", None))

        doc_timestamp = time.time()
        doc_id = f"{doc_hash}_{doc_timestamp}"

        pipeline = [analyzers.DefaultAnalyzer(), analyzers.FileConvertAnalyzer,
                    analyzers.PDFAnalyzer(),
                    analyzers.MetaAnalyzer(), analyzers.TextAnalyzer()]

        new_doc = dict(doc)
        for step in pipeline:
            new_doc = step(new_doc)

        new_doc["hash"] = doc_hash
        new_doc["version"] = doc_timestamp
        new_doc["content"] = doc_hash
        new_doc["raw_content"] = raw_hash
        new_doc["version_key"] = doc_id

        return new_doc, doc_id

    def insert_document(self, doc, doc_id=None):
        """Inserts a document into the index `index` under `doc_id`

        Args:
            doc (dict): the document to insert.
            doc_id (str): the document id, defaults to None.

        Returns:
            es.Response: the response object of elastic search
        """
        new_doc, new_doc_id = self._prepare_document(doc)
        # check whether a document with this hash already exists in the db.
        ex_id = self.exist_document(doc_hash=new_doc["hash"])
        if ex_id is not None:
            return {"result": "existing", "_id": ex_id}

        if doc_id is None:
            doc_id = new_doc_id
        res = self.es.index(index=self.defaults.docs_index(),
                            doc_type=self.defaults.doc_type(),
                            id=doc_id, body=new_doc)
        return res

    def remove_document(self, doc_id, **kwargs):
        """Removes the document with the given id.

        Args:
            doc_id (str): the document's id, that will be removed.

        Returns:
            es.Response: the response object of elastic search
        """
        index = self.defaults.other(kwargs).docs_index()
        doc_type = self.defaults.other(kwargs).doc_type()

        result = self.es.get(index=index, doc_type=doc_type, id=doc_id,
                             _source=["content"])

        if result["found"] is False:
            return result

        self.fs.remove(sda(result, ["_source", "content"]))

        res = self.es.delete(index=self.defaults.docs_index(),
                             doc_type=self.defaults.doc_type(),
                             id=doc_id)
        return res

    def exist_document(self, doc_id=None, doc_hash=None, source_url=None,
                       **kwargs):
        """Checks whether a document for the given features exists.

        It compares `doc_id`, `source_url` and the documents `doc_hash`.
        They are evaluated with an AND.

        Args:
            doc_id (str): the document's id.
            doc_hash (str): the document's sha256-hash.
            source_url (str): the document's 'baseUrl'.

        Returns:
            str: the id of the existing document or None.
        """
        index = self.defaults.other(kwargs).docs_index()
        criteria = [("_id", doc_id), ("hash", doc_hash),
                    ("source.url", source_url)]
        criteria = [{"term": {c[0]: c[1]}} for c in criteria if c[1]]

        query = {
            "size": 1,
            "query": {
                "bool": {
                    "must": criteria
                }
            },
            "_source": False
        }
        result = self.es.search(index=index, body=query)
        return sda(result, ["hits", "hits", 0, "_id"], None)

    def update_document(self, doc_id, update, **kwargs):
        """Updates the given document with the contents of the update-dict.

        Args:
            doc_id (str): the id of the document that is to be updated.
            update (dict): a dict of properties that should be updated.

        Returns:
            dict: an elastic result dict.
        """
        index = self.defaults.other(kwargs).docs_index()
        doc_type = self.defaults.other(kwargs).doc_type()

        if self.exist_document(doc_id=doc_id) is None:
            return {"result": "failed"}

        body = etrans.transform_input(update)

        u_body = {
            "script": {
                "id": "update_body",
                "params": {
                    "body": body
                }
            }
        }
        res = self.es.update(index=index, doc_type=doc_type,
                             id=doc_id, body=u_body)
        return res

    def remove_tag(self, tag, doc_id):
        """Removes tag `tag` from document `doc_id`.

        Args:
            tag (str): the tag to remove.
            doc_id (str): the document id.
        """
        index = self.defaults.docs_index()
        doc_type = self.defaults.doc_type()

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
        index = self.defaults.docs_index()
        doc_type = self.defaults.doc_type()

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
        index = self.defaults.seeds_index()

        res = {}
        try:
            res = self.es.search(index=index, body={
                "query": {"match_all": {}}
            })
        except Exception as e:
            logger.error(f"An error occured while retrieving the seeds. {e}")

        return etrans.transform_output(res)

    def add_seed(self, seed):
        """Adds a new seed to the database.

        Args:
            seed (dict): a dict containing the keys `url`, `name`,
                `description` and [`category`].

        Returns:
            `elasticsearch.Response`: the response of the es database.
        """
        index = self.defaults.seeds_index()
        doc_type = self.defaults.seed_type()

        allowed_keys = ["url", "name", "description", "category"]
        doc = {k: seed.get(k) for k in allowed_keys}
        seed_id = seed["id"]

        result = self.es.index(index=index, doc_type=doc_type,
                               id=seed_id, body=doc)
        return result

    def delete_seed(self, seed_id):
        """Removes a seed from the database.

        Args:
            seed_id (str): the id of the seed

        Returns:
            `elasticsearch.Response`: the response of the es database.
        """
        index = self.defaults.seeds_index()

        result = self.es.delete(index=index, id=seed_id)
        return result

    def get_search(self, search_id):
        """Returns the search saved at a given search_id.

        Args:
            search_id (str): the id ('name') of the query.

        Returns:
            dict: a matching search.
        """
        index = self.defaults.search_index()
        doc_type = self.defaults.search_type()

        res = None
        try:
            res = self.es.get(index=index, doc_type=doc_type, id=search_id)
        except Exception as e:
            logger.error("An error occured while retrieving the searches."
                         f" {e}")

        return etrans.transform_output(res)

    def get_searches(self):
        """Returns the searches saved in the database.

        Returns:
            list: a list of saved searches.
        """
        index = self.defaults.search_index()
        doc_type = self.defaults.search_type()

        res = None
        try:
            res = self.es.search(index=index, doc_type=doc_type, body={
                "query": {"match_all": {}}
            })
        except Exception as e:
            logger.error("An error occured while retrieving the searches."
                         f" {e}")

        if res is not None:
            return etrans.transform_output(res)
        return None

    def add_search(self, search):
        """Adds a new search job to the database.

        Args:
            search (dict): a dict containing the keys:
                `name`, `keywords`, `time_periods`, `file_types` and `sources`.
                The `_id` will be the name or a random id.

        Returns:
            `elasticsearch.Response`: the response of the es database.
        """
        index = self.defaults.search_index()
        doc_type = self.defaults.search_type()

        doc = etrans.transform_search(search)
        allowed = ["name", "keywords", "file_types", "time_periods", "sources"]
        required = ["keywords", "file_types", "time_periods", "sources"]

        try:
            etrans.check_dict(doc, allowed, required)
        except KeyError as e:
            return {
                "result": "failed",
                "message": str(e)
            }
        # create some numbering for the existing search names
        search_id = doc.get("name")
        if not search_id:
            search_id = "Unnamed query"
        org_id = search_id
        i = 2
        while self.es.exists(index=index, doc_type=doc_type, id=search_id,
                             _source=False):
            search_id = f"{org_id}-{i}"
            i += 1

        result = self.es.index(index=index, doc_type=doc_type,
                               id=search_id, body=doc)
        return result

    def delete_search(self, search_id):
        """Removes a seed from the database.

        Args:
            search_id (str): the id of the search, that will be deleted.

        Returns:
            `elasticsearch.Response`: the response of the es database.
        """
        index = self.defaults.search_index()

        result = self.es.delete(index=index, id=search_id)
        return result

    def get_field_values(self, search_text, fields=None, active={}):
        """Returns all possible filters for the documents containing the query.

        Args:
            search_text (str): the text to search for.
            fields (list): a list of fields that should be aggregated.
                Defaults to None, which means all fields.
            active (dict): the filter dict as returned to the normal search.

        Returns:
            dict: a dictionary of aggregations.
        """
        index = self.defaults.docs_index()
        logger.debug(f"Searching for '{search_text or 'all'}' on '{index}'")

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
            # just use aggregations.
            "_source": False,
            "size": 0,
            "query": {
                "bool": {
                    "must": search,
                }
            },
            "aggs": etrans.transform_aggs(fields),
        }
        results = self.es.search(index=index, body=s_body)

        return etrans.transform_agg_filters(results["aggregations"], active)

    def get_document(self, doc_id, fields=None):
        """Returns the document with the given id, displaying only `fields`.

        Args:
            doc_id (str): the `_id` of the given document.
            fields (list): a list of fields that should be returned.
                Defaults to None, which means all fields.

        Returns:
            dict: the document.
        """
        index = self.defaults.docs_index()
        s_body = {
            "size": 1,
            "query": {
                "match": {
                    "_id": doc_id,
                }
            },
            "_source": True
        }

        source, scripted = etrans.transform_fields(fields)
        if source is not None:
            s_body["_source"] = source
        if scripted is not None:
            s_body["script_fields"] = scripted

        results = self.es.search(index=index, body=s_body)
        # construct the document
        docs = etrans.transform_output(results)

        if len(docs) == 0:
            return None
        return docs[0]

    def get_calendar(self, cur_date):
        """Returns the calendar for the given date in a efficient way.

        Args:
            cur_date (datetime.datetime): the date the current dashboard is
                displayed for.

        Returns:
            list: a list of date-dicts.
        """
        index = self.defaults.docs_index()
        start, end = utility.get_year_range(cur_date)
        s_body = {
            # doesn't need results, just aggregations
            "_source": False,
            "size": 0,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": {
                            "range": {
                                "date": {
                                    "gt": start,
                                    "lte": end
                                }
                            }
                        }
                }
            },
            "aggs": {
                "dates": {
                    "terms": {
                        "field": "date",
                        "order": {"_key": "desc"}
                    },
                    "aggs": {
                        "statusses": {
                            "terms": {
                                "field": "status",
                            }
                        }
                    }
                }
            }
        }
        results = self.es.search(index=index, body=s_body)
        return etrans.transform_calendar_aggs(results["aggregations"])

    def get_date(self, cur_date):
        """Returns the date aggregation for the given date in a efficient way.

        Args:
            cur_date (datetime.datetime): the date the aggregation should be
                produced for.

        Returns:
            dict: a calendar date, containing the number of open, waiting and
                assigned documents.
        """
        index = self.defaults.docs_index()
        s_body = {
            "_source": False,
            "size": 0,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": {
                        "range": {
                            "date": {
                                "gt": f"{cur_date:%Y-%m-%d}||-24h/d",
                                "lte": f"{cur_date:%Y-%m-%d}||/d"
                            }
                        }
                    }
                }
            },
            "aggs": {
                "dates": {
                    "terms": {
                        "field": "date",
                        "order": {"_key": "desc"}
                    },
                    "aggs": {
                        "statusses": {
                            "terms": {
                                "field": "status"
                            }
                        }
                    }
                }
            }
        }
        results = self.es.search(index=index, body=s_body)

        date_dict = {
            "date": cur_date,
            "n_open": 0,
            "n_waiting": 0,
            "n_finished": 0
        }

        res_aggs = etrans.transform_calendar_aggs(results["aggregations"])
        if len(res_aggs) > 0:
            return res_aggs[0]
        # if no result was found...
        return date_dict

    def get_uploads(self, cur_date, min_docs=10, fields=None, **kwargs):
        """Returns all past uploads, today's uploads are always included.

        Using the parameter `min_docs` a minimum amount of documents can be
        set, but the number of today's uploads might exceed that minimum.

        Args:
            cur_date (datetime.datetime): today's date.
            min (int): the minimum number of documents retrieved (if possible).
                Defaults to 10.
            fields (list): which fields to be retrieved. Defaults to
                `["document", "metadata.crawl_date"]`
            **kwargs (dict): keyword-arguments to override the classes
                defaults.

        Returns:
            list: a list of documents.
        """
        index = self.defaults.other(kwargs).docs_index()
        doc_type = self.defaults.other(kwargs).doc_type()

        if fields is None:
            fields = ["document", "metadata.crawl_date"]

        # count the number of todays uploads
        c_body = {
            "size": 0,
            "_source": False,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": [
                        {
                            "range": {
                                "metadata.crawl_date": {
                                    "gt": f"{cur_date:%Y-%m-%d}||-24h/d",
                                    "lte": f"{cur_date:%Y-%m-%d}||/d"
                                }
                            }
                        },
                        {
                            "term": {
                                "source.name": "inhouse"
                            }
                        }
                    ]
                }
            }
        }

        counts = self.es.search(index=index, doc_type=doc_type, body=c_body)
        size = max(sda(counts, ["hits", "total"], 0), min_docs)

        s_body = {
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": [
                        {
                            "range": {
                                "metadata.crawl_date": {
                                    "lte": f"{cur_date:%Y-%m-%d}||/d"
                                }
                            }
                        },
                        {
                            "term": {
                                "source.name": "inhouse"
                            }
                        }
                    ]
                }
            },
            "sort": {
                "metadata.crawl_date": {"order": "desc"}
            }
        }
        # append additional fields
        source, scripted = etrans.transform_fields(fields)
        if source:
            s_body["_source"] = source
        if scripted:
            s_body["script_fields"] = scripted

        results = self.es.search(index=index, doc_type=doc_type, body=s_body)
        docs = etrans.transform_output(results)
        return docs

    def get_documents(self, cur_date, fields=None, sort_by=None, **kwargs):
        """Returns all documents with the given date.

        Args:
            cur_date (datetime.date): the date for which the documents should
                be queried.
            fields (list): a list of fields that should be queried.
                Defaults to `["impact", "type", "category", "document",
                "change", "reading_time", "status"]`
            sort_by (dict): a dict holding the keys: `keyword` to sort after,
                "order", accepting "asc" or "desc" and optionally "args" for
                additional arguments. Defaults to None.

        Returns:
            list: a list of documents in an easy processable format.
        """
        index = self.defaults.other(kwargs).docs_index()
        doc_type = self.defaults.other(kwargs).doc_type()
        size = self.defaults.other(kwargs).size()

        if fields is None:
            fields = ["impact", "type", "category", "document", "change",
                      "reading_time", "status"]
        s_body = {
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": {
                        "range": {
                            "date": {
                                "gt": f"{cur_date:%Y-%m-%d}||-24h/d",
                                "lte": f"{cur_date:%Y-%m-%d}||/d"
                            }
                        }
                    }
                }
            },
            "sort": etrans.transform_sortby(sort_by)
        }
        # append additional fields
        source, scripted = etrans.transform_fields(fields)
        if source is not None:
            s_body["_source"] = source
        if scripted is not None:
            s_body["script_fields"] = scripted

        results = self.es.search(index=index, doc_type=doc_type, body=s_body)
        docs = etrans.transform_output(results)
        return docs

    def get_connected(self, doc_id, fields=None, **kwargs):
        """Returns all connected documents.

        Args:
            doc_id (str): the document whose connections should be found.
            fields (list): a list of fields that should be queried.
                Defaults to `["date", "impact", "type", "category", "document",
                "reading_time", "status", "fingerprint", "connections"]`

        Returns:
            list: a list of connected documents.
        """
        index = self.defaults.other(kwargs).docs_index()
        min_sim = self.defaults.other(kwargs).min_similarity(0.5)
        size = self.defaults.other(kwargs).size()

        if fields is None:
            fields = ["date", "impact", "type", "category", "document",
                      "reading_time", "status", "fingerprint", "connections"]

        conn_field = f"connections.{doc_id}"
        s_body = {
            "size": size,
            "query": {
                "bool": {
                    "must": {
                        "exists": {
                            "field": conn_field
                        }
                    },
                    "filter": {
                        "range": {
                            f"{conn_field}.similarity": {
                                "gte": min_sim,
                            }
                        }
                    }
                }
            }
        }
        # append additional fields
        source, scripted = etrans.transform_fields(fields)
        if source is not None:
            s_body["_source"] = source
        if scripted is not None:
            s_body["script_fields"] = scripted

        results = self.es.search(index=index, body=s_body)
        docs = etrans.transform_output(results)
        return docs

    def get_versions(self, doc_id, fields=None, **kwargs):
        """Returns all documents, that are a version of the given doc_id.

        Args:
            doc_id (str): the document, whose versions should be retrieved.
            fields (list): a list of fields that should be queried.
                Defaults to `["date", "impact", "type", "category", "document",
                "reading_time", "status", "fingerprint", "connections"]`

        Returns:
            list: a list of documents, which are versions of each other.
        """
        index = self.defaults.other(kwargs).docs_index()

        if fields is None:
            fields = ["date", "fingerprint", "document"]

        s_body = {
            "query": {
                "bool": {
                    "must": {
                        "term": {
                            "version_key": doc_id
                        }
                    },
                    # exclude self
                    "must_not": {
                        "term": {
                            "_id": doc_id
                        }
                    }
                }
            }
        }
        # append additional fields
        source, scripted = etrans.transform_fields(fields)
        if source is not None:
            s_body["_source"] = source
        if scripted is not None:
            s_body["script_fields"] = scripted

        results = self.es.search(index=index, body=s_body)
        docs = etrans.transform_output(results)
        return docs

    def get_content(self, doc_id, **kwargs):
        """Returns the content of the given document.

        Args:
            doc_id (str): the document, whose content should be retrieved.

        Returns:
            bytes: content of the saved file.
        """
        index = self.defaults.other(kwargs).docs_index()
        doc_type = self.defaults.other(kwargs).doc_type()

        result = self.es.get(index=index, doc_type=doc_type, id=doc_id,
                             _source=["content"])

        if result["found"] is False:
            return None

        return self.fs.get(sda(result, ["_source", "content"]))

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
        index = self.defaults.docs_index()
        logger.debug(f"Searching for {search_text} on '{index}'")

        start = (page - 1) * self.defaults.size()
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
            "size": self.defaults.size(),
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
        docs = etrans.transform_output(results)

        num_pages, rem = divmod(results["hits"]["total"], self.defaults.size())
        if rem > 0:
            num_pages += 1

        return {
            "num_results": results["hits"]["total"],
            "total_pages": num_pages,
            "results": docs,
            "aggs": etrans.transform_agg_filters(results.get("aggregations"))
        }
