"""This module provides an interface to APScheduler for adding crawling-jobs.

It provides the class Scheduler which realizes this behaviour.

Author: Johannes Müller <j.mueller@reply.de>
"""
from pytz import utc

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
import cerberus

import crawlers
import utility


def _find_subclasses(klass):
    """Recursive search for subclasses of a class.

    Returns:
        set: a set of classes.
    """
    subclasses = set(klass.__subclasses__())
    subclasses.union(*[_find_subclasses(k) for k in subclasses])
    return subclasses


def _detect_crawlers():
    """Returns a dict, mapping a crawlers name to a class.

    It returns all classes, that are subclasses of crawlers.plugin.BasePlugin.

    Returns:
        dict: a dictionary mapping class name to class.
    """
    subclasses = _find_subclasses(crawlers.plugin.BasePlugin)
    return {s.__name__: s for s in subclasses}


SCHEMATA = {
    "job": lambda params: {
        "id": {"type": "string", "nullable": True, "required": False},
        "crawler": {
            "type": "dict",
            "allow_unknown": True,
            "schema": {
                "id": {
                    "type": "string",
                    "required": True,
                },
            },
        },
        "schedule": {
            "type": "dict",
            "allow_unknown": True,
            "schema": {
                "id": {
                    "type": "string",
                    "required": True,
                    "allowed": params["trigger_ids"]
                },
                "name": {"type": "string", "required": False},
                "options": {
                    "type": "list",
                    "empty": True,
                    "schema": {
                        "type": "dict",
                        "allow_unknown": True,
                        "schema": {
                            "id": {
                                "type": "integer",
                                "coerce": int,
                                "required": True
                            },
                            "name": {"type": "string", "required": False},
                            "active": {
                                "type": "boolean",
                                "coerce": utility.coerce_bool,
                                "required": True
                            }
                        }
                    }
                }
            },
        },
        "next_run": {"type": "datetime", "required": False}
    }
}


class Scheduler:
    TRIGGERS = {
        "trig_hourly": {
            "name": "Each hour",
            "options": [],
            "schema": {"type": "dict", "allow_unknown": True},
            "trigger_args": lambda args: dict(hour="*")
        },
        "trig_daily": {
            "name": "Each day",
            "options": [],
            "schema": {"type": "dict", "allow_unknown": True},
            "trigger_args": lambda args: dict(day="*")
        },
        "trig_weekday": {
            "name": "Each weekday",
            "options": [{"id": idx, "name": el} for idx, el in
                        enumerate("Sun Mon Tue Wed Thu Fri Sat".split())],
            "schema": {
                "id": {
                    "type": "integer",
                    "coerce": int,
                    "min": 0,
                    "max": 6
                },
                "name": {"type": "string", "required": False},
                "active": {
                    "type": "boolean",
                    "coerce": utility.coerce_bool,
                    "required": True
                }
            },
            "trigger_args": lambda args:
                dict(day_of_week=",".join(str(a) for a in args))
        },
        "trig_monthly": {
            "name": "Each month",
            "options": [{"id": idx+1, "name": el} for idx, el in
                        enumerate(("Jan Feb Mar Apr May Jun "
                                   "Jul Aug Sep Oct Nov Dec").split())],
            "schema": {
                "id": {
                    "type": "integer",
                    "coerce": int,
                    "min": 0,
                    "max": 12
                },
                "name": {"type": "string", "required": False},
                "active": {
                    "type": "boolean",
                    "coerce": utility.coerce_bool,
                    "required": True
                }
            },
            "trigger_args": lambda args:
                dict(month=",".join(str(a) for a in args))
        }
    }
    """Predefined triggers and their argument checks."""

    def __init__(self, mongo_collection, crawler_dir="crawlers",
                 crawler_args={}, **cron_defaults):
        """Initializes the scheduler by binding it to it's mongodb.

        Args:
            mongo_collection (pymongo.collection.Collection): The collection
                where the crawling jobs should be saved to.
            crawler_dir (str): the directory, where the crawlers will be found.
                Defaults to "crawlers".
            job_defaults (dict): a dictionary of keyword arguments for
                the schedulers job_defaults.
            **cron_defaults (dict): a dictionary of keyword arguments for
                the schedulers job_defaults.

        Returns:
            Scheduler: a fresh Scheduler instance.
        """
        jobstores = {
            "default": {"type": "memory"},
            "mongo": MongoDBJobStore(database=mongo_collection.database.name,
                                     collection=mongo_collection.name,
                                     client=mongo_collection.database.client)
        }

        executors = {
            "default": ThreadPoolExecutor(),
            "processpool": ProcessPoolExecutor()
        }

        self.crawler_defaults = utility.DefaultDict(crawler_args)

        self.cron_defaults = utility.DefaultDict({
            # standard is every day at 00:00:00
            "hour": 0,
            "minute": 0,
            "second": 0
        }, **cron_defaults)

        self.scheduler = BackgroundScheduler(jobstores=jobstores,
                                             executors=executors,
                                             timezone=utc)

        self.crawlers = _detect_crawlers()
        # set up the validator schema.
        self.job_validator = cerberus.Validator(SCHEMATA["job"]({
            "trigger_ids": list(self.TRIGGERS)
        }))
        self.scheduler.start()

    def upsert_job(self, job_dict, **crawler_args):
        """Adds or updates a job using the provided user_input.

        If an id field is present in the dict, the job is updated, otherwise
        a new one is created.

        Args:
            job_dict (dict): user input for a job, as defined in `SCHEMATA`.
            **crawler_args (dict): additional arguments for the crawler
                (especially `elastic` is needed).

        Returns:
            apscheduler.job.Job: a new job Object.
        """
        if self.job_validator(job_dict):
            raise(AssertionError(str(self.job_validator.errors)))

        doc = utility.SDA(job_dict)

        args = self.crawler_defaults.other(crawler_args).dict
        job = self.crawlers.get(doc["crawler.id"], None)
        # default to the SearchPlugin, and give the search name as argument.
        if job is None:
            inst = self.crawlers["SearchPlugin"](search_id=doc["crawler.id"],
                                                 **args)
        else:
            inst = job(**args)
        trigger = self._make_trigger(doc["schedule"])

        if doc["id"]:
            new_job = self.scheduler.modify_job(doc["id"], jobstore="mongo",
                                                func=inst,
                                                trigger=trigger,
                                                name=doc["name"])
        else:
            new_job = self.scheduler.add_job(inst, jobstore="mongo",
                                             trigger=trigger,
                                             name=doc["name"])

        return new_job

    def raw_add_job(self, crawler, crawler_args={}, **cron_args):
        """Adds a job to the scheduler using the provided arguments.

        Args:
            crawler_args (dict): the arguments passed to the crawler
                initialization.
            **cron_args (dict): the arguments for setting the cron job.

        Returns:
            apscheduler.job.Job: a job object.
        """
        job = self.crawlers[crawler]
        # initialize the given crawler
        job_inst = job(**crawler_args)
        # check for a given trigger id:
        if cron_args.has("id"):
            trigger = self.get_trigger(cron_args["id"], cron_args.get("args"))
            new_job = self.scheduler.add_job(job_inst, trigger)
        else:
            args = self.cron_defaults.other(cron_args)
            new_job = self.scheduler.add_job(job_inst, "cron", args)
        return new_job.id

    def get_triggers(self):
        """Returns a list of triggers, that are predefined in the system.

        Returns:
            list: a list of tuples, holding id and name for each trigger.
        """
        return [{"id": k, "name": v["name"], "options": v["options"]}
                for k, v in self.TRIGGERS.items()]

    def sync_jobs(self, joblist):
        """Synchronize the current jobs with a given list of jobs.

        This means, that all jobs not included in the list will be removed,
        existing ones will be updated and new ones will be added to the
        scheduler.

        Args:
            joblist (list): a list of jobs in the format of the schema.

        Returns:
            bool: whether this operation was successful or not.
        """
        current_jobs = self.get_jobs()
        jobs_to_keep = {j["id"] for j in joblist if j.get("id")}

        # remove old jobs
        for job in current_jobs:
            if job["id"] not in jobs_to_keep:
                self.scheduler.remove_job(job["id"], jobstore="mongo")

        # update and add jobs
        for job in joblist:
            self.upsert_job(job)

        return True

    def _make_trigger(self, trigger_doc):
        """Creates a trigger from a given dictionary of user input."""
        # we can assume, that an id for the trigger is given in the input.
        cur_trigger = self.TRIGGERS[trigger_doc["id"]]
        option_validator = cerberus.Validator(cur_trigger["schema"])

        args = [o["id"] for o in trigger_doc["options"]
                if option_validator(o) and o["active"]]

        trigger_args = cur_trigger["trigger_args"](args)
        return CronTrigger(**trigger_args)

    def get_jobs(self):
        """Returns a list of jobs that are scheduled in the system.

        Returns:
            list: a list of job-dicts, holding the id and the runtimes.
        """
        jobs = self.scheduler.get_jobs()
        joblist = []
        for job in jobs:
            joblist.append({
                "id": job.id,
                "name": job.name,
                "crawler": job.func.__name__,
                "schedule": job.trigger,
                "next_run": job.next_run_time
            })
        return joblist
