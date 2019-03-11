from __future__ import absolute_import
import warnings
import base64
import logging

from apscheduler.jobstores.base import (
    BaseJobStore, JobLookupError, ConflictingIdError
)
from apscheduler.util import (
    maybe_ref, datetime_to_utc_timestamp, utc_timestamp_to_datetime
)
from apscheduler.job import Job

try:
    import cPickle as pickle
except ImportError:  # pragma: nocover
    import pickle

try:
    import elasticsearch
except ImportError:  # pragma: nocover
    raise ImportError("ElasticJobStore needs elasticsearch to be installed.")

from utility import SDA

logger = logging.getLogger(__name__)


class ElasticJobStore(BaseJobStore):
    """
    Stores jobs in an elasticsearch database.

    Args:
        index (str): the name of the index to use for the jobs.
            Defaults to "jobs".
        client (elasticsearch.ElasticSearch): an elasticsearch-client,
            when no connection arguments should be given. Defaults to `None`.
        pickle_protocol (int): pickle protocol level to use
            (for serialization), defaults to the highest available.
        size (int): the max number of jobs that should be returned in a query.
            Defaults to 100.
        **connection_args (dict): the connection arguments that will be passed
            directly to the elasticsearch client.
    """
    JOB_MAPPING = {
        "properties": {
            "id": {"type": "keyword"},
            "next_run_time": {"type": "date"},
            "job_state": {"type": "binary"}
        }
    }

    UPDATE_SCRIPT = {
        "script": {
            "lang": "painless",
            "source": """
                for (k in params.body.keySet()) {
                    ctx._source[k] = params.body[k];
                }
            """
        }
    }

    def __init__(self, index="jobs", doc_type="apscheduler", client=None,
                 pickle_protocol=pickle.HIGHEST_PROTOCOL, size=100,
                 **connect_args):
        super(ElasticJobStore, self).__init__()
        self.pickle_protocol = pickle_protocol

        if not index:
            raise ValueError("The 'index' parameter must not be empty")
        self.index = index

        if not doc_type:
            raise ValueError("The 'doc_type' parameter must not be empty")
        self.doc_type = doc_type
        self.size = size

        if client:
            self.client = maybe_ref(client)
        else:
            self.client = elasticsearch.Elasticsearch(**connect_args)

    def start(self, scheduler, alias):
        super(ElasticJobStore, self).start(scheduler, alias)
        self.client.put_script(id="update_body", body=self.UPDATE_SCRIPT)

        if not self.client.indices.exists(index=self.index):
            self.client.indices.create(index=self.index)
            # put the mapping into the docs index
            self.client.indices.put_mapping(index=self.index,
                                            doc_type=self.doc_type,
                                            body=self.JOB_MAPPING)

    @property
    def connection(self):
        warnings.warn(("The 'connection' member is deprecated -- use 'client' "
                       "instead"), DeprecationWarning)
        return self.client

    def lookup_job(self, job_id):
        result = self.client.get(index=self.index, doc_type=self.doc_type,
                                 id=job_id, _source=["job_state"])

        job_state = SDA(result)["_source.job_state"]
        if job_state:
            return self._reconstitute_job(job_state)
        return None

    def get_due_jobs(self, now):
        timestamp = datetime_to_utc_timestamp(now)
        search_body = {
            "size": self.size,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": [
                        {
                            "range": {
                                "next_run_time": {
                                    "lte": timestamp
                                }
                            }
                        }
                    ]
                }
            },
            "sort": {
                "next_run_time": {"order": "asc"}
            }
        }
        return self._get_jobs(search_body)

    def get_next_run_time(self):
        search_body = {
            "size": 1,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    },
                    "filter": [
                        {
                            "exists": {
                                "field": "next_run_time"
                            }
                        }
                    ]
                }
            },
            "sort": {
                "next_run_time": {"order": "asc"}
            }
        }
        result = self.client.search(index=self.index, doc_type=self.doc_type,
                                    body=search_body)
        next_run_time = SDA(result)["hits.hits.0._source.next_run_time"]
        if not next_run_time:
            return None
        return utc_timestamp_to_datetime(next_run_time)

    def get_all_jobs(self):
        search_body = {
            "size": self.size,
            "query": {
                "bool": {
                    "must": {
                        "match_all": {}
                    }
                }
            },
            "sort": {
                "next_run_time": {"order": "asc"}
            }
        }
        jobs = self._get_jobs(search_body)

        self._fix_paused_jobs_sorting(jobs)
        return jobs

    def add_job(self, job):
        doc = {
            "id": job.id,
            "next_run_time": datetime_to_utc_timestamp(job.next_run_time),
            "job_state":
                base64.b64encode(pickle.dumps(job.__getstate__(),
                                              self.pickle_protocol)).decode()
            }
        result = self.client.index(index=self.index, doc_type=self.doc_type,
                                   id=job.id, body=doc, refresh=True)
        if SDA(result, 0)["_shards.successful"] == 0:
            raise ConflictingIdError(job.id)

    def update_job(self, job):
        changes = {
            "next_run_time": datetime_to_utc_timestamp(job.next_run_time),
            "job_state":
                base64.b64encode(pickle.dumps(job.__getstate__(),
                                              self.pickle_protocol)).decode()
        }
        upd_body = {
            "doc": changes
        }
        result = self.client.update(index=self.index, doc_type=self.doc_type,
                                    id=job.id, body=upd_body, refresh=True)
        if SDA(result, 0)["_shards.failed"] > 0:
            raise JobLookupError(job.id)

    def remove_job(self, job_id):
        result = self.client.delete(index=self.index, doc_type=self.doc_type,
                                    id=job_id)
        if SDA(result, 0)["_shards.successful"] == 0:
            raise JobLookupError(job_id)

    def remove_all_jobs(self):
        self.client.delete_by_query(index=self.index,
                                    doc_type=self.doc_type,
                                    body={"query": {"march_all": {}}})

    def shutdown(self):
        pass

    def _reconstitute_job(self, job_state):
        logger.debug("Trying to reconstitute job from job state")
        job_state = pickle.loads(base64.b64decode(job_state))
        job = Job.__new__(Job)
        job.__setstate__(job_state)
        job._scheduler = self._scheduler
        job._jobstore_alias = self._alias
        return job

    def _get_jobs(self, conditions):
        jobs = []
        failed_ids = []
        result = self.client.search(index=self.index, doc_type=self.doc_type,
                                    body=conditions)
        for doc in SDA(result)["hits.hits"]:
            doc = SDA(doc)
            try:
                jobs.append(self._reconstitute_job(doc["_source.job_state"]))
            except BaseException:
                self._logger.exception(
                    "Unable to restore job '%s' -- removing it",
                    doc["_id"]
                )
                failed_ids.append(doc["_id"])

        # Remove all the jobs we failed to restore
        if failed_ids:
            self.client.delete_by_query(index=self.index,
                                        doc_type=self.doc_type,
                                        body={
                                            "query": {
                                                "ids": {
                                                    "values": failed_ids}}})
        return jobs

    def __repr__(self):
        return '<%s (client=%s)>' % (self.__class__.__name__, self.client)


class InjectorJobStore(ElasticJobStore):
    """This Store allows injecting a dictionary of dynamic args into the jobs.

    These dynamic arguments are appended to the jobs.kwargs, before executing.
    """

    def __init__(self, args=[], kwargs={}, **js_args):
        """Initializes a new Elastic JobStore, inject arguments at runtime.

        Args:
            args (list): list of arguments to inject into the job.
            kwargs (dict): dictionary of keyword arguments to inject.
            **js_args (dict): additional arguments for the jobstore.

        Returns:
            `InjectorJobStore`: a new InjectorJobStore.
        """
        super().__init__(**js_args)
        self.args = tuple(args)
        self.kwargs = kwargs

    def _reconstitute_job(self, job_state):
        # add the keyword arguments
        job = super()._reconstitute_job(job_state)
        job.args = job.args + self.args
        job.kwargs = dict(job.kwargs, **self.kwargs)
        logger.debug(f"Reconstituted job {job.id} with the following kwargs: "
                     f"'{job.kwargs}'")
        return job

    def add_job(self, job):
        # remove the runtime arguments
        copy = self._remove_rtargs(job)
        super().add_job(copy)

    def update_job(self, job):
        # remove the runtime arguments
        copy = self._remove_rtargs(job)
        logger.debug(f"Updating job: {job.id}, remaining kwargs: {job.kwargs}")
        super().update_job(copy)

    def _remove_rtargs(self, job):
        # remove all runtime arguments, that are already saved in the
        # injector, use a copy of the job, such that the threading error is
        # resolved.
        copy = Job.__new__(Job)
        copy.__setstate__(job.__getstate__())
        if len(self.args) > 0:
            copy.args = copy.args[:-len(self.args)]
        copy.kwargs = {k: v for k, v in copy.kwargs.items()
                       if k not in self.kwargs}
        return copy
