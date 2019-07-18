"""The Plugin for the BaFin-webpage.

The Idea is to use the rss feed as the source of news and and update
the database accordingly.

The connected files have to be considered recursively...

Author: Johannes Mueller <j.mueller@reply.de>
"""
import datetime as dt
import locale
import re
from urllib.parse import urljoin
import logging

from lxml import html

from crawlers.plugin import BasePlugin, PaginatedResource, XPathResource

import utility as ut


URL_TEMPLATE = ("https://www.bafin.de/SiteGlobals/Forms/Suche/"
                "Servicesuche_Formular.html?input_=7844616"
                "&gts=7855320_list%253DdateOfIssue_dt%252Bdesc"
                "&gtp=7855320_list%253D{page}"
                "&resourceId=7844738"
                "&language_={locale}"
                "&pageLocale={locale}")


def _make_resource_path(path, cwd):
    """Takes a relative `path` and a `cwd` and returns an absolute  path.

    Also cuts away the unnecessary jsessionid.

    Args:
        path (str): the relative path (containing '.' and '.')
        cwd (str): the current working directory, to root the paths.

    Returns:
        str: a new absolute path
    """
    if path is None:
        return None
    without_jsessionid = re.sub(r";jsessionid=[^?]+((?:\?.+)?)$", r"\1", path)
    return urljoin(cwd, without_jsessionid)


def _convert_date(date_string):
    """Converts the date from a given date string:

    Example `vom 20. November 2018`
    """
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})", date_string)

    doc_date = dt.datetime.now()
    # date is given using german locale...
    for loc in ["de_DE", "German"]:
        try:
            locale.setlocale(locale.LC_TIME, loc)
        except locale.Error as le:
            logging.error(f"Couldn't set locale string '{loc}'.")
    if match:
        doc_date = dt.datetime.strptime(match[1], "%d.%m.%Y")
    # reset locale
    locale.setlocale(locale.LC_TIME, "")
    return doc_date


def _unescape_string(some_string):
    """Remove all silent-hyphens from a string.

    Example: `_unescape_string('Fi\\xadnanz')  # => 'Finanz'`
    """
    return some_string.replace("\xad", "")


class BafinPlugin(BasePlugin):

    CWD = "https://www.bafin.de"
    """Directory to use when localizing the relative paths."""

    source_name = "BaFin"
    """Name that should be displayed as source."""

    entry_path = XPathResource(
        "//div[contains(normalize-space(@class), 'search-result ')]",
    )
    date_path = XPathResource(
        """
        ./h3/span/span[@class = 'metadata']/span[contains(text(),
                                                 'Erscheinung')]
        /following-sibling::text()
        """,
        after=[ut.defer("__getitem__", 0), _convert_date]
    )
    detail_path = XPathResource(
        "./h3/a/@href",
        after=[ut.defer("__getitem__", 0),
               ut.curry(_make_resource_path, cwd=CWD)]
    )
    title_path = XPathResource(
        "string(./h3/a)",
        after=[_unescape_string]
    )
    type_path = XPathResource(
        """
        normalize-space(
            ./h3/span/span[@class = 'metadata']/span[contains(text(),
                                                    'Format:')]
            /following-sibling::text()
        )
        """,
        after=[ut.defer("split", ", ")]
    )
    topic_path = XPathResource(
        """
        normalize-space(
            ./h3/span/span[@class = 'thema']/a/text()
        )
        """,
        after=[ut.defer("split", ", ")]
    )
    doc_path = XPathResource(
        "./ul[@class = 'links']/li[1]/a/@href",
        after=[ut.defer("__getitem__", 0),
               ut.curry(_make_resource_path, cwd=CWD)])

    content_path = XPathResource(
        "//div[@id = 'content']"
    )

    connected_path = XPathResource(
        ".//a[contains(@class, 'RichTextIntLink ')]/@href"
    )

    def __init__(self, elastic):
        super().__init__(elastic)
        # bafin needs a faked user-agent in the headers.
        self.entry_resource = PaginatedResource(URL_TEMPLATE)

    def find_entries(self, page):
        docs = []
        for entry in self.entry_path(page):
            doc = ut.SDA({}, "N/A")
            doc["metadata.date"] = self.date_path(entry)
            doc["metadata.title"] = self.title_path(entry)
            doc["metadata.detail_url"] = self.detail_path(entry)
            doc["metadata.url"] = self.doc_path(entry)
            if doc["metadata.url"] is None:
                doc["metadata.url"] = doc["metadata.detail_url"]
            doc["metadata.topic"] = self.topic_path(entry)
            doc["metadata.type"] = self.type_path(entry)
            docs.append(doc.a_dict)

        return docs

    def process_document(self, document, **kwargs):
        doc = ut.SDA(document)
        resp = self.url_fetcher(doc["metadata.detail_url"])
        tree = html.fromstring(resp.content)
        content = self.content_path(tree)
        doc["metadata.mentionned"] = [_make_resource_path(e, self.CWD)
                                      for e in self.connected_path(content)]
        return doc.a_dict
