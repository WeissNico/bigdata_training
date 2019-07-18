"""Holds the `BasePlugin` and the `PluginManager`.

Author: Johannes Müller <j.mueller@reply.de>
"""
from abc import abstractmethod
import logging
import requests
from lxml import etree, html
import time
from functools import reduce
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import queue

import utility


logger = logging.getLogger(__name__)


def _flat_map(func, iterable):
    """Runs a function func on each element in an iterator.

    It returns a flat list (not a nested one).
    If the function returns no list types, this is a normal map.

    BE CAREFUL WITH STRINGS.

    Args:
        func (function): the function to run.
        iterable (iterable): the input elements.

    Returns:
        list: a flat list.
    """

    def _red_func(acc, el):
        res = func(el)
        # check if the resulting is a list in a way that supports duck typing
        lst = None
        try:
            lst = list(res)
        except ValueError as e:
            logger.error("Tried to convert a non iterable type to list.")

        if lst is not None:
            acc += lst
        elif res is not None:
            acc.append(res)
        return acc

    return reduce(_red_func, iterable, [])


def _retry_connection(url, method="get", max_retries=3, **kwargs):
    """Repeats the connection with increasing pauses until an answer arrives.

    This should ease out of the 10054 Error, that windows throws.

    Args:
        url (str): the destination url.
        method (str): a valid HTTP verb, defaults to "get".
        max_retries (int): the number of maximum retries.
        kwargs (dict): keyword arguments for requests.

    Returns:
        `requests.Response`: the response from the website.
    """
    retry = 0
    response = None
    # create an default dictionary for the request arguments.
    defaults = utility.DefaultDict({
        "headers": {"User-Agent": "Sherlock/0.0.1"}
    })

    while response is None and retry < max_retries:
        try:
            with requests.Session() as s:
                logger.debug(f"Try to {method.upper()} to '{url}'.")
                response = s.request(method, url, **(defaults.other(kwargs)))
        except requests.exceptions.ConnectionError as connErr:
            # sleep increasing (exponential time intervals)
            logger.error("Detected an Error while connecting... "
                         f"retry ({retry})")
            time.sleep(2 ** retry)
    return response


class XPathResource:
    """An XPathResource that can be called with a tree object.

    Attributes:
        xpath (etree.XPath): the resources xpath.
        args (dict): a dictionary of arguments for the xpath.
        before (callable): the function to call before running the expression
            on each of the trees elements.
        after (callable): the function to call after running the xpath on each
            of the results.
    """

    def __init__(self, xpath, args=None, before=None, after=None):
        """Initialize a new XPathResource.

        Args:
            xpath (str): the resources xpath.
            args (dict): a dictionary of named arguments for the xpath.
        """
        if isinstance(xpath, etree.XPath):
            self.xpath = xpath
        else:
            self.xpath = etree.XPath(xpath)
        self.args = args
        if args is None:
            self.args = {}
        self.before = before
        if before is None:
            self.before = []
        self.after = after
        if after is None:
            self.after = []
        self.results = []

    def __call__(self, tree):
        for func in self.before:
            try:
                tree = func(tree)
            except (AttributeError, ValueError, IndexError, TypeError) as err:
                logger.error(f"Before function '{func.__name__}' failed.")
                tree = []

        if isinstance(tree, list):
            self.results = _flat_map(self.xpath, tree)
        else:
            self.results = self.xpath(tree)

        for func in self.after:
            try:
                self.results = func(self.results)
            except (AttributeError, ValueError, IndexError, TypeError) as err:
                logger.error(f"After function '{func.__name__}' failed.")
                self.results = None
        return self.results

    def each(self, func, inplace=False, **args):
        collect = []
        for res in self.results:
            collect.append(func(res, **args))
        if inplace:
            self.results = collect
        return collect


class PaginatedResource:
    """Simple class for mapping a paginated source url.

    Yields the html etree one after another.

    Attributes:
        url_template (str): An format-string, using the variable `page` as
            wildcard for the page.
        min_page (int): the number to start iterating the pages.
        max_page (int): the maximum page, defaults to None.
        locale (str): the locale string used on this resource.
        url_fetcher (callable): a callable taking a url as argument and returns
            a `requests.Response`. Defaults to _retry_connection.
    """
    def __init__(self, url_template, min_page=1, max_page=None, page_step=1,
                 locale="de", **fetch_args):
        """Initialize the `PaginatedResults`.

        Args:
            url_template (str): A format-string, using the variable `page` as
                wildcard for the page.
            min_page (int): the number to start iterating the pages.
            max_page (int): the maximum page, defaults to None.
            page_step (int): the step-size between two pages.
            locale (str): the locale to use. Defaults to "de".
            **fetch_args (dict): keyword-args that get passed to the fetcher.
        """
        self.url_template = url_template
        self.min_page = min_page
        self.max_page = max_page
        self.step = page_step
        self._cur_page = min_page
        self._fetch_args = fetch_args
        self.locale = locale
        self.url_fetcher = _retry_connection

    def __iter__(self):
        return self

    def __next__(self):
        if self.max_page and (self._cur_page > self.max_page):
            raise StopIteration
        resp = self.url_fetcher(self.url_template.format(page=self._cur_page,
                                                         locale=self.locale),
                                "get",
                                **self._fetch_args)
        if resp.status_code != 200:
            raise StopIteration
        self._cur_page += self.step
        return html.fromstring(resp.content)


class BasePlugin:
    """Holds all the base functionality of a plugin.

    Provides a binding to the database and holds all the links already found.

    Attributes:
        elastic (elastic.Elastic: an interface to the elastic-db.
        entry_resource (iterable): An iterator providing the urls to crawl for
            entries. Defaults to `PaginatedResource`.
        content_converters (dict): Mapping from content-type to converter,
            such that a valid pdf-file is returned.
        documents (list): a list of entries, found during the last crawl.
    """

    source_name = "No Name"
    """Name that should be displayed as source."""

    def __init__(self, elastic, fetch_limit=None, initial=False,
                 queue_size=100):
        super(BasePlugin, self).__init__()
        self.elastic = elastic
        self.defaults = utility.DefaultDict({
            "limit": fetch_limit,
            "initial": initial,
        })
        self.url_fetcher = _retry_connection
        self.entry_resource = []
        self.docq = queue.Queue(maxsize=queue_size)

    def __call__(self, **kwargs):
        """Runs the plugin, by fetching all documents and saving them.

        This is achieved by using several queues.

        Args:
            **kwargs (dict): keyword arguments that will be passed on to all
                steps.
        """
        with ThreadPoolExecutor(max_workers=20) as ex:
            # retrieve all documents (initial list of tasks)
            working_futures = {
                ex.submit(self.get_documents, **kwargs): "Docs retrieved!"
            }
            # while there are working threads:
            while working_futures:
                # check for status of the threads
                done, _ = wait(working_futures, timeout=2,
                               return_when=FIRST_COMPLETED)
                # check the queue for new items.. with a timeout of 5 secs
                try:
                    item = self.docq.get(timeout=5)
                except queue.Empty:
                    logger.debug("Timed out waiting for new docs!")
                else:
                    # if there is a new item, submit a new worker.
                    cur_fut = ex.submit(self._chained_process, item, **kwargs)
                    working_futures[cur_fut] = f"processing document {item[0]}"
                # work on finished futures
                for future in done:
                    msg = working_futures[future]
                    # check whether an exception was thrown:
                    try:
                        future.result()
                    except Exception as exc:
                        logger.exception(
                            f"An exception was caught while {msg}! {exc}"
                        )
                    else:
                        if msg.startswith("processing"):
                            self.docq.task_done()
                        logger.info(f"Finished {msg}!")
                    # remove future from list.
                    del working_futures[future]

    def get_documents(self, limit=None, initial=None, **kwargs):
        """Fetches new entries for the given resource and places them in a
        queue (`self.process_docq`).

        Args:
            limit (int): maximum number of entries to pull.
            initial (bool): whether an initial run should be done?
                An initial run does not halt, when a document appeared prev.
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            BasePlugin: self.
        """
        limit = self.defaults.limit.also(limit)
        initial = self.defaults.initial.also(initial)
        has_unseen_docs = True
        doc_count = 0
        for page in self.entry_resource:
            # insert the entries into documents, if they aren't already tracked
            cur_docs = self.find_entries(page, **kwargs)

            # if there are no documents on the page, break
            if len(cur_docs) == 0:
                logger.info(f"No documents found on page {page}!")

            for doc in cur_docs:
                doc = utility.SDA(doc)
                doc_url = doc["metadata.url"]
                # skip entries where no url is given
                if not doc_url:
                    logger.debug("Document contains no url. SKIP.")
                    continue
                exists = self.elastic.exist_document(source_url=doc_url)

                # handle existing files, if they have a date field, which lies
                # in the past, break the loop.
                if exists:
                    logger.debug(f"Document for url '{doc_url}' does already "
                                 "exist. SKIP.")
                    doc_date = doc["metadata.date"]
                    today = utility.from_date()
                    if (not initial) and doc_date and doc_date < today:
                        logger.debug("Document's date lies in the past."
                                     "Stop search.")
                        has_unseen_docs = False
                        break
                    continue

                logger.info(f"Found document {doc_url}.")
                doc["metadata.source"] = self.source_name
                # enter documents to processing queue.
                self.docq.put((doc_count, doc.a_dict))
                doc_count += 1

                # break when the number of retrieved documents reaches the
                # limit
                if limit and doc_count >= limit:
                    has_unseen_docs = False
                    break

            # check whether there are still unseen documents, else do not
            # continue searching
            if has_unseen_docs is False:
                break
        return self

    def _chained_process(self, dox, **kwargs):
        pipeline = [self.process_documents,
                    self.download_documents,
                    self.insert_documents]
        for step in pipeline:
            dox = step(dox, **kwargs)
        return dox

    def process_documents(self, dox, **kwargs):
        """Process the documents.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.
            dox (tuple): index and document to work on.

        Returns:
            int: the current index of the document.
        """
        idx, doc = dox
        logger.info(f"Processing doc {idx}...")
        pdoc = self.process_document(doc, **kwargs)

        return idx, pdoc

    def download_documents(self, dox, **kwargs):
        """Downloads the content of `metadata.url` and writes it to content.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            int: the current index of the document.
        """
        idx, doc = dox
        logger.info(f"Downloading doc {idx}...")
        ddoc = self.download_document(doc)
        logger.info(f"Got content type {ddoc['content_type']} for doc {idx}.")

        return idx, ddoc

    def insert_documents(self, dox, **kwargs):
        """Inserts the documents into the database.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            int: the current index of the document.
        """
        idx, doc = dox
        if doc["raw_content"]:
            logger.info(f"Analyzing doc {idx} and inserting it into the DB...")
            res = self.elastic.insert_document(doc)
            if res["result"] == "created":
                logger.info(f"Successfully inserted document {idx} into DB.")
        else:
            logger.info("Doc contains no content. SKIP")

        return idx

    def download_document(self, document, **kwargs):
        """Fetches the url of a document and sets the content of the document.

        Args:
            document (dict): the document that should be prepared, expects
                at least an "url" key.
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            dict: a document with added "content" field.
        """
        # fetch body
        doc_url = utility.SDA(document)["metadata.url"]
        if not doc_url:
            document["raw_content"] = None
            return document
        resp = self.url_fetcher(doc_url)
        content_type = resp.headers.get("content-type", None)
        document["content_type"] = content_type
        document["raw_content"] = resp.content
        return document

    @abstractmethod
    def find_entries(self, page, **kwargs):
        """Find the entries in the given page and return them as a list.

        Args:
            page (lxml.etree): a html ressource, a result page.
            **kwargs (dict): additional keyword-arguments.

        Returns:
            list: a list of documents holding the url and some metadata.
        """

    @abstractmethod
    def process_document(self, document, **kwargs):
        """Process a given document.

        Args:
            document (dict): a document, providing at least an "url", "date"
                and "metadata" field.
            **kwargs (dict): additional keyword-arguments.

        Returns:
            dict: an enriched document.
        """
