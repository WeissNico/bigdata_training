"""This module provides an interface to APScheduler for adding crawling-jobs.

It provides the class Scheduler which realizes this behaviour.

Author: Johannes Müller <j.mueller@reply.de>
"""
from pytz import utc

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.cron import CronTrigger
import cerberus

import crawlers
import utility
import logging
from scheduler.elasticjobstore import InjectorJobStore

logger = logging.getLogger(__name__)


def _run_plugin(crawler_by_ref, run_args=None, **init_args):
    """A wrapper for allowing to run the given crawler from global scope.

    It simply instanciates the plugin with init_args, and then runs it
    using the run_args.

    Args:
        run_args (dict): a dictionary of arguments that should be passed
            to the crawlers runtime.
        **init_args (dict): a dictionary of arguments that should be passed
            to the initialization of the plugin.
    """
    if run_args is None:
        run_args = {}
    crawler = _detect_crawlers()[crawler_by_ref]
    logger.info(f"Starting up crawler '{crawler.__name__}'.")
    logger.debug(f"Received run_args: {run_args} and init_args: {init_args}.")
    instance = crawler(**init_args)
    instance(**run_args)
    logger.info(f"Crawler '{crawler.__name__}' finished.")


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
            "schema": {
                "id": {
                    "type": "string",
                    "required": True,
                },
            },
        },
        "schedule": {
            "type": "dict",
            "schema": {
                "id": {
                    "type": "string",
                    "required": True,
                    "allowed": params["trigger_ids"]
                },
                "name": {"type": "string", "required": False},
                "options": {
                    "type": "list",
                    "minlength": 0,
                    "schema": {
                        "type": "dict",
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
        "next_run": {"type": "dict", "required": False}
    }
}


class Scheduler:
    TRIGGERS = {
        "trig_5minutes": {
            "id": "trig_5minutes",
            "name": "Every five minutes",
            "options": [],
            "schema": {},
            "trigger_args": lambda args: dict(minute="*/5"),
            "from_trigger": lambda trig: []
        },
        "trig_hourly": {
            "id": "trig_hourly",
            "name": "Each hour",
            "options": [],
            "schema": {},
            "trigger_args": lambda args: dict(hour="*"),
            "from_trigger": lambda trig: []
        },
        "trig_daily": {
            "id": "trig_daily",
            "name": "Each day",
            "options": [],
            "schema": {},
            "trigger_args": lambda args: dict(day="*"),
            "from_trigger": lambda trig: []
        },
        "trig_weekday": {
            "id": "trig_weekday",
            "name": "Each weekday",
            "options": [{"id": i, "name": el, "active": True} for i, el in
                        enumerate("Mon Tue Wed Thu Fri Sat Sun".split())],
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
                dict(day_of_week=",".join(str(a) for a in args)),
            "from_trigger": lambda trig:
                [int(d) for d in str(trig.fields[4]).split(",")]
        },
        "trig_monthly": {
            "id": "trig_monthly",
            "name": "Each month",
            "options": [{"id": i+1, "name": el, "active": True} for i, el in
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
                dict(month=",".join(str(a) for a in args)),
            "from_trigger": lambda trig:
                [int(d) for d in str(trig.fields[1]).split(",")]
        },
    }
    """Predefined triggers and their argument checks."""

    def __init__(self, elastic, crawler_dir="crawlers",
                 crawler_args={}, **cron_defaults):
        """Initializes the scheduler by binding it to it's elasticsearch db.

        Args:
            elastic (elasticsearch.Elasticsearh): The es-client to save the
                crawling jobs in.
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
            "elastic": InjectorJobStore(kwargs=crawler_args, client=elastic)
        }

        executors = {
            "default": ThreadPoolExecutor(10),
            "processpool": ProcessPoolExecutor(10)
        }

        job_defaults = {
            "misfire_grace_time": 5*60,  # 5min
            "coalesce": True,
        }

        self.cron_defaults = utility.DefaultDict({
            # standard is every day at 00:00:00
            "hour": 0,
            "minute": 0,
            "second": 0
        }, **cron_defaults)

        self.scheduler = BackgroundScheduler(jobstores=jobstores,
                                             executors=executors,
                                             job_defaults=job_defaults,
                                             timezone=utc)

        self.crawlers = _detect_crawlers()
        # set up the validator schema.
        self.job_validator = cerberus.Validator(SCHEMATA["job"]({
            "trigger_ids": list(self.TRIGGERS)
        }), allow_unknown=True)
        self.scheduler.start()

    def upsert_job(self, job_dict, **runtime_args):
        """Adds or updates a job using the provided user_input.

        If an id field is present in the dict, the job is updated, otherwise
        a new one is created.

        Args:
            job_dict (dict): user input for a job, as defined in `SCHEMATA`.
            **runtime_args (dict): additional runtime arguments for the
                crawler.

        Returns:
            apscheduler.job.Job: a new job Object.
        """
        if not self.job_validator.validate(job_dict):
            raise(AssertionError(str(self.job_validator.errors)))

        doc = utility.SDA(job_dict)

        job = self.crawlers.get(doc["crawler.id"], None)
        # default to the SearchPlugin, and give the search name as argument.
        if job is None:
            inst = {
                "args": (
                    "SearchPlugin",
                    runtime_args
                ),
                "kwargs": dict(search_id=doc["crawler.id"])
            }
        else:
            inst = {
                "args": (
                    doc["crawler.id"],
                    runtime_args
                ),
                "kwargs": {}
            }
        trigger = self._make_trigger(doc["schedule"])

        if doc["id"]:
            self.scheduler.modify_job(doc["id"], jobstore="elastic",
                                      func=_run_plugin,
                                      name=doc["name.name"], **inst)
            new_job = self.scheduler.reschedule_job(doc["id"],
                                                    jobstore="elastic",
                                                    trigger=trigger)
        else:
            # use the crawler id as name, when the job is created.
            new_job = self.scheduler.add_job(_run_plugin,
                                             jobstore="elastic",
                                             trigger=trigger,
                                             name=doc["crawler.id"], **inst)

        return new_job

    def get_triggers(self):
        """Returns a list of triggers, that are predefined in the system.

        Returns:
            list: a list of tuples, holding id and name for each trigger.
        """
        return [{"id": v["id"], "name": v["name"], "options": v["options"]}
                for v in self.TRIGGERS.values()]

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
        logger.debug("Syncing job lists ...")
        current_jobs = self.get_jobs()
        jobs_to_keep = {j["id"] for j in joblist if j.get("id")}

        # remove old jobs
        for job in current_jobs:
            if job["id"] not in jobs_to_keep:
                self.scheduler.remove_job(job["id"], jobstore="elastic")

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

    def _serialize_trigger(self, trigger):
        """Serializes a trigger into a json array, as defined in TRIGGERS."""
        # since we only have a defined set of triggers, the following is
        # possible.
        mapping = [(v["trigger_args"]([]).keys(), k) for k, v
                   in self.TRIGGERS.items()]

        trigger_doc = None
        result = {}
        for keys, name in mapping:
            # all keys for the mapping need to be defined.
            def_keys = [f.name for f in trigger.fields if not f.is_default]
            if all([(key in def_keys) for key in keys]):
                trigger_doc = self.TRIGGERS[name]
                break

        if not trigger_doc:
            return result

        result["name"] = trigger_doc["name"]
        result["id"] = trigger_doc["id"]
        args = set(trigger_doc["from_trigger"](trigger))
        # copy the list of options (otherwise this leads to nasty side effects)
        options = [dict(**item) for item in trigger_doc["options"]]
        for option in options:
            option["active"] = option["id"] in args
        result["options"] = options

        return result

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
                "name": {"name": job.name},
                "crawler": {"id": job.args[0]},
                "schedule": self._serialize_trigger(job.trigger),
                "next_run": {
                    "name": job.next_run_time
                }
            })
        logger.debug(f"Retrieved {len(joblist)} jobs from the jobstore.")
        return joblist

    def run_job(self, job_id):
        """Runs the job with the specified id immediately.

        Args:
            job_id: the id of the job that should be run.

        Returns:
            bool: whether running the job succeeded or not.
        """
        logger.debug(f"Running job '{job_id}' directly.")
        cur_job = self.scheduler.get_job(job_id, jobstore="elastic")
        if cur_job is None:
            return False

        cur_job.func(*cur_job.args, **cur_job.kwargs)
        return True
