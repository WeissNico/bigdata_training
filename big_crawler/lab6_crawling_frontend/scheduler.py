"""This module provides an interface to APScheduler for adding crawling-jobs.

It provides the class Scheduler which realizes this behaviour.

Author: Johannes Müller <j.mueller@reply.de>
"""
from pytz import utc

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

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


class Scheduler:
    def __init__(self, mongo_collection, crawler_dir="crawlers",
                 job_defaults={}, **cron_defaults):
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

        self.job_defaults = utility.DefaultDict(job_defaults)
        self.cron_defaults = utility.DefaultDict({
            # standard is every day at 00:00:00
            "hour": 0,
            "minute": 0,
            "second": 0
        }, **cron_defaults)

        self.scheduler = BackgroundScheduler(jobstores=jobstores,
                                             executors=executors,
                                             defaults=job_defaults,
                                             timezone=utc)

        self.crawlers = _detect_crawlers()
        self.scheduler.start()

    def add_job(self, crawler, crawler_args={}, **cron_args):
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
        new_job = self.scheduler.add_job(job_inst, "cron",
                                         self.cron_defaults.other(cron_args))
        return new_job.id

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
                "crawler": job.func.__name__,
                "arguments": job.kwargs,
                "schedule": job.trigger,
                "next_run": job.next_run_time
            })
        return joblist
