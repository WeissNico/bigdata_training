"""Holds the `BasePlugin` and the `PluginManager`.

Author: Johannes Müller <j.mueller@reply.de>
"""
import logging
import requests
from lxml import etree, html
import time
from functools import reduce
import io

import weasyprint

import utility


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
            logging.error("Tried to convert a non iterable type to list.")

        if lst is not None:
            acc += lst
        elif res is not None:
            acc.append(res)
        return acc

    return reduce(_red_func, iterable, [])


def _retry_connection(url, method, max_retries=10, **kwargs):
    """Repeats the connection with increasing pauses until an answer arrives.

    This should ease out of the 10054 Error, that windows throws.

    Args:
        url (str): the destination url.
        method (str): a valid HTTP verb.
        max_retries (int): the number of maximum retries.
        kwargs (dict): keyword arguments for requests.

    Returns:
        `requests.Response`: the response from the website.
    """
    retry = 0
    response = None

    while response is None and retry < max_retries:
        try:
            with requests.Session() as s:
                logging.debug(f"Try to {method.upper()} to '{url}'.")
                response = s.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as connErr:
            # sleep increasing (exponential time intervals)
            logging.error("Detected an Error while connecting... "
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
            tree = map(func, tree)
        self.results = _flat_map(self.xpath, tree)
        for func in self.after:
            self.results = map(func, self.results)
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
        url_fetcher (callable): a callable taking a url as argument and returns
            a `requests.Response`. Defaults to _retry_connection.
    """
    def __init__(self, url_template, min_page=1, max_page=None, **fetch_args):
        """Initialize the `PaginatedResults`.

        Args:
            url_template (str): A format-string, using the variable `page` as
                wildcard for the page.
            min_page (int): the number to start iterating the pages.
            max_page (int): the maximum page, defaults to None.
            **kwargs (dict): keyword-arguments that get passed to the fetcher.
        """
        self.url_template = url_template
        self.min_page = min_page
        self.max_page = max_page
        self._cur_page = min_page
        self._fetch_args = fetch_args
        self.url_fetcher = _retry_connection

    def __iter__(self):
        return self

    def __next__(self):
        if self._cur_page > self._max_page:
            raise StopIteration
        resp = self.url_fetcher(self.url_template.format(page=self._cur_page),
                                "get",
                                **self._fetch_args)
        if not resp:
            raise StopIteration
        self._cur_page += 1
        return html.fromstring(resp.content)


class BaseConverter:

    def __init__(self):
        self.url_fetcher = _retry_connection

    def convert(self, content):
        return content

    def __call__(self, url, **fetch_args):
        resp = self.url_fetcher(url, "get", **fetch_args)
        ret = self.convert(resp.content)
        return ret


class PDFConverter(BaseConverter):
    """Simple Converter for the pdf mime-type.

    Just fetches the content and returns it.
    """
    pass


class HTMLConverter(BaseConverter):
    """Simple Converter for the html mime-type.

    Just fetches the content and converts it using weasyprint.
    """
    def __init__(self, content_xpath=None):
        """Initializes the HTML converter.

        Args:
            content_xpath (etree.XPath): an XPath pointing to the relevant
                html portions. Defaults to
                `//head | //div[@id='content']`
                for fetching the css metadata and the content-div.
        """
        super().__init__()
        self.content_xpath = content_xpath
        if content_xpath is None:
            self.content_xpath = etree.XPath("//head | //div[@id='content']")

    def convert(self, content):
        tree = html.fromstring(content)
        relevant_html = self.content_xpath(tree)
        stream = io.BytesIO()
        doc = weasyprint.HTML(string=relevant_html.tostring())
        doc.write_pdf(stream)
        return stream.getvalue()


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

    content_converters = {
        "application/pdf": PDFConverter(),
        "text/html": HTMLConverter()
    }

    def __init__(self, elastic):
        self.elastic = elastic
        self.url_fetcher = _retry_connection
        self.entry_resource = []
        self.documents = []

    def __call__(self, limit=100, **kwargs):
        """Fetches new entries for the given resource.

        Args:
            limit (int): maximum number of entries to pull.

        Returns:
            BasePlugin: self.
        """
        has_unseen_docs = True
        doc_count = 0
        for page in self.entry_resource:
            # insert the entries into documents, if they aren't already tracked
            for doc in self.find_entries(page, **kwargs):
                doc_url = doc.get("url")
                # skip entries where no url is given
                if not doc_url:
                    logging.debug("Document contains no url. SKIP.")
                    continue
                exists = self.elastic.exist_document(source_url=doc_url)

                # handle existing files, if they have a date field, which lies
                # in the past, break the loop.
                if exists:
                    logging.debug(f"Document for url '{doc_url}' does already "
                                  "exist. SKIP.")
                    doc_date = doc.get("date")
                    today = utility.from_date()
                    if doc_date and doc_date < today:
                        logging.debug("Document's date lies in the past."
                                      "Stop search.")
                        has_unseen_docs = False
                        break
                    continue

                self.documents.append(doc)
                doc_count += 1

                # break when the number of retrieved documents reaches the
                # limit
                if doc_count >= limit:
                    has_unseen_docs = False
                    break

            # check whether there are still unseen documents, else do not
            # continue searching
            if has_unseen_docs is False:
                break
        return self

    def find_entries(self, page, **kwargs):
        """Find the entries in the given page and return them as a list.

        THIS MUST BE OVERRIDEN IN THE CHILDREN.

        Args:
            page (lxml.etree): a html ressource, a result page.
            **kwargs (dict): additional keyword-arguments.

        Returns:
            list: a list of documents holding the url and some metadata.
        """
        return []

    def process_documents(self, **kwargs):
        """Process the documents.

        Args:
            **kwargs (dict): additional keyword-arguments.

        Returns:
            BasePlugin: self.
        """
        for doc in self.documents:
            self.process_document(doc, **kwargs)
        return self

    def convert(self, mimetype, content):
        """Converts the given content with the given mimetype to pdf.

        Args:
            mimetype (str): the mimetype.
            content (bytes): the content of the file.

        Returns:
            bytes: the converted content.
        """
        conv = self.content_converters.get(mimetype, BaseConverter())
        return conv(content)

    def convert_document(self, document, **kwargs):
        """Fetches the url of a document and sets the content of the document.

        Args:
            document (dict): the document that should be prepared, expects
                at least an "url" key.

        Returns:
            dict: a document with added "content" field.
        """
        # fetch body
        doc_url = document.get("url")
        if not doc_url:
            document["content"] = None
            return document
        resp = _retry_connection(doc_url, "get")
        content_type = resp.headers["content-type"]
        content = self.convert(content_type, resp.content)
        document["content"] = content
        return document

    def process_document(self, document, **kwargs):
        """Process a given document.

        THIS SHOULD BE OVERRIDEN IN THE CHILDREN.

        Args:
            document (dict): a document, providing at least an "url", "date"
                and "metadata" field.
            **kwargs (dict): additional keyword-arguments.

        Returns:
            dict: an enriched document.
        """
        return document

    def insert_documents(self, **kwargs):
        """Inserts the documents into the database.

        Args:
            **kwargs (dict): additional keyword-arguments.

        Returns:
            int: the number of newly inserted documents.
        """
        doc_count = 0
        for doc in self.documents:
            res = self.elastic.insert_document(doc)
            if res["action"] == "created":
                doc_count += 1
        return doc_count
