"""Holds the `BasePlugin` and the `PluginManager`.

Author: Johannes Müller <j.mueller@reply.de>
"""
from abc import abstractmethod
import logging
import requests
from lxml import etree, html
from urllib.parse import urljoin, urlparse
import time
from functools import reduce

import pdfkit

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


def _retry_connection(url, method="get", max_retries=10, **kwargs):
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
        "headers": {"user-agent": "Sherlock/0.0.1"}
    })

    while response is None and retry < max_retries:
        try:
            with requests.Session() as s:
                logging.debug(f"Try to {method.upper()} to '{url}'.")
                response = s.request(method, url, **(defaults.other(kwargs)))
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
            try:
                tree = func(tree)
            except (AttributeError, ValueError, IndexError, TypeError) as err:
                logging.error(f"Before function '{func.__name__}' failed.")
                tree = []

        if isinstance(tree, list):
            self.results = _flat_map(self.xpath, tree)
        else:
            self.results = self.xpath(tree)

        for func in self.after:
            try:
                self.results = func(self.results)
            except (AttributeError, ValueError, IndexError, TypeError) as err:
                logging.error(f"After function '{func.__name__}' failed.")
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
    def __init__(self, url_template, min_page=1, max_page=None, locale="de",
                 **fetch_args):
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
        if not resp:
            raise StopIteration
        self._cur_page += 1
        return html.fromstring(resp.content)


class BaseConverter:

    def __init__(self):
        super(BaseConverter, self).__init__()

    @abstractmethod
    def convert(self, content, **kwargs):
        """Converts the content into another format.

        Args:
            content (bytes): some content.
            **kwargs (dict): additional parameters used in the implementations
                convert method.

        Returns:
            bytes: content in a different format.
        """

    def __call__(self, content, **additional_args):
        """Converts the content into another format.

        Args:
            content (bytes): some content.
            **additional_args (dict): additional args to pass to the convert
                function.

        Returns:
            bytes: content in a different format.
        """
        ret = self.convert(content, **additional_args)
        return ret


class PDFConverter(BaseConverter):
    """Simple Converter for the pdf mime-type.

    Just fetches the content and returns it.
    """
    def convert(self, content, **kwargs):
        return content


class HTMLConverter(BaseConverter):
    """Simple Converter for the html mime-type.

    Just fetches the content and converts it using weasyprint.
    """
    def __init__(self, content_xpath=None):
        """Initializes the HTML converter.

        Args:
            content_xpath (etree.XPath): an XPath pointing to the relevant
                html portions. Defaults to `//body`
                for fetching all the contents of the page.
        """
        super().__init__()

        self.content_xpath = content_xpath
        if content_xpath is None:
            self.content_xpath = XPathResource(
                "//body"
            )
        self.head_xpath = XPathResource(
            "//head"
        )
        self.link_xpath = XPathResource(
            "//*[@href or @src]"
        )
        self.base_xpath = XPathResource(
            "//head/base/@href",
            after=[utility.defer("__getitem__", 0)]
        )
        self.pdfkit_config = pdfkit.configuration(
            wkhtmltopdf=utility.path_in_project("wkhtmltopdf", True)
        )

    def _replace_relative(self, tree, base_url):
        """Replaces relative href and src attributes.

        Args:
            tree (lxml.etree): An html-ETree.
            base_url (str): the base url.
        """
        for elem in self.link_xpath(tree):
            for attr in ["href", "src"]:
                if attr not in elem.attrib:
                    continue
                elem.attrib[attr] = urljoin(base_url, elem.attrib[attr])

    def convert(self, content, **kwargs):
        tree = html.fromstring(content)
        # retrieve base url from kwargs
        base_url = kwargs.get("base_url", None)
        base_url_found = self.base_xpath(tree)
        if base_url_found:
            base_url = base_url_found
        # replace relative links
        self._replace_relative(tree, base_url)
        relevant_html = self.head_xpath(tree)
        relevant_html.extend(self.content_xpath(tree))
        # stringify the portions together
        html_string = "\n".join([html.tostring(part).decode("utf-8")
                                 for part in relevant_html])
        doc = pdfkit.from_string(html_string, False,  # css=stylesheets,
                                 configuration=self.pdfkit_config)
        return doc


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

    content_converters = {
        "application/pdf": PDFConverter(),
        "text/html": HTMLConverter()
    }

    def __init__(self, elastic):
        super(BasePlugin, self).__init__()
        self.elastic = elastic
        self.url_fetcher = _retry_connection
        self.entry_resource = []
        self.documents = []

    def __call__(self, **kwargs):
        """Runs the plugin, by fetching all documents and saving them.

        Args:
            **kwargs (dict): keyword arguments that will be passed on to all
                steps.
        """
        self.get_documents(**kwargs)
        self.process_documents(**kwargs)
        self.convert_documents(**kwargs)
        self.insert_documents(**kwargs)

    def get_documents(self, limit=20, **kwargs):
        """Fetches new entries for the given resource.

        Args:
            limit (int): maximum number of entries to pull.
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            BasePlugin: self.
        """
        has_unseen_docs = True
        doc_count = 0
        for page in self.entry_resource:
            # insert the entries into documents, if they aren't already tracked
            for doc in self.find_entries(page, **kwargs):
                doc = utility.SDA(doc)
                doc_url = doc["metadata.url"]
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
                    doc_date = doc["metadata.date"]
                    today = utility.from_date()
                    if doc_date and doc_date < today:
                        logging.debug("Document's date lies in the past."
                                      "Stop search.")
                        has_unseen_docs = False
                        break
                    continue

                logging.info(f"Found document {doc_url}.")
                doc["metadata.source"] = self.source_name
                self.documents.append(doc.a_dict)
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

    def process_documents(self, **kwargs):
        """Process the documents.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            BasePlugin: self.
        """
        for idx, doc in enumerate(self.documents):
            logging.info(f"Processing doc {idx} of {len(self.documents)}...")
            self.process_document(doc, **kwargs)
        return self

    def convert_documents(self, **kwargs):
        """Converts all included documents to pdf.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            BasePlugin: self.
        """
        for idx, doc in enumerate(self.documents):
            logging.info(f"Converting doc {idx} of {len(self.documents)}...")
            self.convert_document(doc)
        return self

    def insert_documents(self, **kwargs):
        """Inserts the documents into the database.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            int: the number of newly inserted documents.
        """
        doc_count = 0
        for idx, doc in enumerate(self.documents):
            logging.info(f"Inserting doc {idx} of {len(self.documents)}"
                         " into the database.")
            res = self.elastic.insert_document(doc)
            if res["result"] == "created":
                doc_count += 1
        return doc_count

    def convert(self, mimetype, content, **kwargs):
        """Converts the given content with the given mimetype to pdf.

        Args:
            mimetype (str): the mimetype.
            content (bytes): the content of the file.
            **kwargs (dict): passed on to the converter.

        Returns:
            bytes: the converted content.
        """
        mime, *args = mimetype.split(";")
        for arg in args:
            kw, *vals = arg.strip(" .,;:_").split("=")
            kwargs[kw] = vals and vals[0]

        conv = self.content_converters.get(mime, BaseConverter())
        return conv(content, **kwargs)

    def convert_document(self, document, **kwargs):
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
            document["content"] = None
            return document
        resp = self.url_fetcher(doc_url)
        content_type = resp.headers["content-type"]
        url_parts = urlparse(doc_url)
        url_stem = f"{url_parts[0]}://{url_parts[1]}/"
        content = self.convert(content_type, resp.content, base_url=url_stem)
        document["content"] = content
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
