"""Holds the `BasePlugin` and the `PluginManager`.

Author: Johannes Müller <j.mueller@reply.de>
"""
from abc import abstractmethod
import logging
import requests
from lxml import etree, html
from urllib.parse import urljoin
import time
from functools import reduce
from concurrent.futures import ThreadPoolExecutor
import re
import os
import shutil
import subprocess
import tempfile

import pdfkit

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
        if not resp:
            raise StopIteration
        self._cur_page += self.step
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


class DummyConverter(BaseConverter):
    """Simple Converter for the most mime-types.

    Just fetches the content and returns it.
    """
    def convert(self, content, **kwargs):
        return content


class EmptyConverter(BaseConverter):
    """Converter that just returns None."""
    def convert(self, content, **kwargs):
        return None


class OfficeConverter(BaseConverter):
    """Simple Converter for all LibreOffice-Supported formats.

    TODO: PUT THIS IN A SEPERATE ANALYZER, maybe.
    Just fetches the content and returns it.
    """
    def convert(self, content, **kwargs):
        path_to_exc = utility.path_in_project("soffice", True)
        if not (os.path.exists(path_to_exc) or shutil.which(path_to_exc)):
            raise ValueError(f"The current path '{path_to_exc}' does not lead "
                             " to an actual file.")

        pdf = None
        try:
            with tempfile.TemporaryDirectory(prefix=".pdfconv_") as tmp_dir:
                tmp_off = os.path.join(tmp_dir, "office")
                tmp_pdf = os.path.join(tmp_dir, "office.pdf")

                pdf = self._convert_to_pdf(content, path_to_exc, tmp_off,
                                           tmp_pdf, **kwargs)
        # catch oserrors caused by anti-virus software.
        except OSError as ose:
            logging.error("Supressed an OSError while handling the "
                          " temp-folder.")
        return pdf

    def _convert_to_pdf(self, content, executable, tmp_off, tmp_pdf, **kwargs):
        with open(tmp_off, "wb") as in_file:
            in_file.write(content)

        command = [executable,
                   "--headless",  # headless mode for conversion
                   "--convert-to pdf",  # target format
                   tmp_off]

        logging.info(f"Running command '{' '.join(command)}'")
        process = subprocess.Popen(command)

        ret = process.wait()
        if ret != 0:
            raise IOError("Couldn't extract any text information.")
        return ret

        content = None
        with open(tmp_pdf, "rb") as out_file:
            content = out_file.read()
        return content


class HTMLConverter(BaseConverter):
    """Simple Converter for the html mime-type.

    Just fetches the content and converts it using wkhtmltopdf.
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
        self.style_xpath = XPathResource(
            "//style[@type = 'text/css' and contains(text(), 'url(')]"
        )
        self.base_xpath = XPathResource(
            "//head/base/@href",
            after=[utility.defer("__getitem__", 0)]
        )
        # treat windows specially
        if utility.PLATFORM == "win32":
            self.pdfkit_config = pdfkit.configuration(
                wkhtmltopdf=utility.path_in_project("wkhtmltopdf", True)
            )
        else:
            self.pdfkit_config = pdfkit.configuration()

    def _replace_relative(self, tree, base_url):
        """Replaces relative href and src attributes.

        Args:
            tree (lxml.etree): An html-ETree.
            base_url (str): the base url.
        """
        def _replace_css_url(match):
            return (match.group(1) + urljoin(base_url, match.group(2)) +
                    match.group(3))

        # replace in the attributes
        for elem in self.link_xpath(tree):
            for attr in ["href", "src"]:
                if attr not in elem.attrib:
                    continue
                elem.attrib[attr] = urljoin(base_url, elem.attrib[attr])
        # replace in css
        for elem in self.style_xpath(tree):
            elem.text = re.sub(r"(url\()([^\)]+)(\))", _replace_css_url,
                               elem.text)
            links = re.findall(r"url\(([^\)]+)\)", elem.text)
            for link in links:
                elem.addnext(
                    etree.XML(f"<link rel='stylesheet' href='{link}' />")
                )

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
        try:
            doc = pdfkit.from_string(html_string, False,
                                     configuration=self.pdfkit_config)
        except IOError as ioe:
            logger.warning("Skipped a document due to wkhtmltopdf failure.")
            return None
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
        "application/pdf": DummyConverter(),
        "text/html": HTMLConverter(),
        # "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        #     OfficeConverter(),
        # ("application/vnd.openxmlformats-officedocument.wordprocessingml"
        #     ".document"):
        #     OfficeConverter(),
        # "application/msword": OfficeConverter(),
        # "application/msexcel": OfficeConverter(),
        # "application/mspowerpoint": OfficeConverter(),
        # "application/vnd.oasis.opendocument.text": OfficeConverter(),
        # "application/vnd.oasis.opendocument.spreadsheet": OfficeConverter(),
        # "application/vnd.oasis.opendocument.presentation": OfficeConverter(),
    }

    def __init__(self, elastic, fetch_limit=1200):
        super(BasePlugin, self).__init__()
        self.elastic = elastic
        self.defaults = utility.DefaultDict({
            "limit": fetch_limit
        })
        self.url_fetcher = _retry_connection
        self.entry_resource = []
        self.documents = []
        self.threaded_executor = ThreadPoolExecutor(max_workers=10)

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

    def get_documents(self, limit=None, **kwargs):
        """Fetches new entries for the given resource.

        Args:
            limit (int): maximum number of entries to pull.
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            BasePlugin: self.
        """
        limit = self.defaults.limit.also(limit)
        has_unseen_docs = True
        doc_count = 0
        for page in self.entry_resource:
            # insert the entries into documents, if they aren't already tracked
            cur_docs = self.find_entries(page, **kwargs)
            # if there are no documents on the page, break
            if len(cur_docs) == 0:
                logger.info(f"No documents found on page {page}!")
                has_unseen_docs = False

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
                    if doc_date and doc_date < today:
                        logger.debug("Document's date lies in the past."
                                     "Stop search.")
                        has_unseen_docs = False
                        break
                    continue

                logger.info(f"Found document {doc_url}.")
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
        def process_loop(enumerated):
            idx, doc = enumerated
            logger.info(f"Processing doc {idx+1} of {len(self.documents)}...")
            self.process_document(doc, **kwargs)
            return 1

        logger.info("--- Start processing the new documents.")
        futures = self.threaded_executor.map(process_loop,
                                             enumerate(self.documents))

        logger.info(f"--- Done: Processed {sum(futures)} documents.")

        return self

    def convert_documents(self, **kwargs):
        """Converts all included documents to pdf.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            BasePlugin: self.
        """
        def process_loop(enumerated):
            idx, doc = enumerated
            logger.info(f"Converting doc {idx+1} of {len(self.documents)}...")
            self.convert_document(doc)
            return 1

        logger.info("--- Start converting the new documents.")
        futures = self.threaded_executor.map(process_loop,
                                             enumerate(self.documents))
        logger.info(f"--- Done: Converted {sum(futures)} documents.")

        return self

    def insert_documents(self, **kwargs):
        """Inserts the documents into the database.

        Args:
            **kwargs (dict): additional keyword args, which are only consumed.

        Returns:
            int: the number of newly inserted documents.
        """
        def process_loop(enumerated):
            idx, doc = enumerated
            if doc["content"]:
                logger.info(f"Inserting doc {idx+1} of {len(self.documents)}"
                            " into the database.")
                res = self.elastic.insert_document(doc)
                if res["result"] == "created":
                    return 1
            logger.info("Doc contains no content. SKIP")
            return 0

        logger.info("--- Start inserting the new documents into the db.")
        futures = self.threaded_executor.map(process_loop,
                                             enumerate(self.documents))
        logger.info(f"--- Done: Inserted {sum(futures)} documents.")
        return sum(futures)

    def convert(self, mimetype, content, **kwargs):
        """Converts the given content with the given mimetype to pdf.

        Args:
            mimetype (str): the mimetype.
            content (bytes): the content of the file.
            **kwargs (dict): passed on to the converter.

        Returns:
            bytes: the converted content.
        """
        logging.info(f"Converting document with MIME-type: {mimetype}.")
        if not mimetype:
            return None

        mime, *args = mimetype.split(";")
        for arg in args:
            kw, *vals = arg.strip(" .,;:_").split("=")
            kwargs[kw] = vals and vals[0]

        conv = self.content_converters.get(mime)
        # sort out unknown mimetypes.
        if not conv:
            logging.info(f"Failed to find a content converter for {mime}.")
            conv = EmptyConverter()
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
        content_type = resp.headers.get("content-type", None)
        content = self.convert(content_type, resp.content, base_url=doc_url)
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
