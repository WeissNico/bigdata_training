"""The Plugin for the eurlex-webpage.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import datetime as dt
import re

from lxml import etree, html

from crawlers.plugin import BasePlugin, PaginatedResource, XPathResource

import utility as ut


URL_TEMPLATE = ("https://eur-lex.europa.eu/search.html?lang={locale}"
                "&type=quick&scope=EURLEX&sortOneOrder=desc"
                "&sortOne=DD&locale={locale}&page={page}")


def _make_resource_path(path, cwd):
    """Takes a relative `path` and a `cwd` and returns an absolute  path.

    Also cuts away the unnecessary `rid` and `qid` attributes.

    Args:
        path (str): the relative path (containing '.' and '.')
        cwd (str): the current working directory, to root the paths.

    Returns:
        str: a new absolute path
    """
    # TODO make more general.
    without_rid_qid = re.sub(r"([?&][qr]id=[^&]+)", "", path)
    with_server = without_rid_qid.replace(".", cwd)
    return with_server.replace("AUTO", "DE/ALL")


def _string_join(context, elements, separator):
    ret = str(separator).join(elements)
    return ret


def _convert_date(date_string):
    """Converts the date from a given DD/MM/YYYY string"""
    match = re.search(r"(\d+\/\d+\/\d+)", date_string)

    doc_date = dt.datetime.now()
    if match:
        doc_date = dt.datetime.strptime(match[1], "%d/%m/%Y")
    return doc_date


class EurlexPlugin(BasePlugin):

    CWD = "https://eur-lex.europa.eu"
    """Directory to use when localizing the relative paths."""

    source_name = "EurLex"
    """Name that should be displayed as source."""

    entry_path = XPathResource("//div[@class = 'SearchResult']")
    date_path = XPathResource(
        """
        .//dl/dd[preceding-sibling::dt[contains(text(), 'Date') or
                                       contains(text(), 'Datum')]]/text()
        """,
        after=[ut.defer("__getitem__", 0), _convert_date])
    doc_path = XPathResource(
        """
        .//ul[contains(@class, 'SearchResultDoc')]/li
        /a[contains(@href, 'PDF') or contains(@href, 'HTML')]/@href
        """,
        after=[ut.defer("__getitem__", 0),
               ut.curry(_make_resource_path, cwd=CWD)]
    )
    title_path = XPathResource(".//h2/a[@class = 'title']/text()",
                               after=[ut.defer("__getitem__", 0)])
    detail_path = XPathResource(".//h2/a[@class = 'title']/@href",
                                after=[ut.defer("__getitem__", 0),
                                       ut.curry(_make_resource_path, cwd=CWD)])

    meta_path = XPathResource("//dl[contains(@class, 'NMetadata')]/dd")
    key_path = XPathResource("normalize-space(./preceding-sibling::dt[1])",
                             after=[ut.defer("strip", " .:,;!?-_#")])
    value_path = XPathResource(
        """
        normalize-space(
            string-join(
                ./text() | .//*[self::span[@lang] or
                                self::a[not(child::span)] or
                                self::i[not(child::span)]]/text(), "#"
            )
        )
        """,
        after=[ut.defer("strip", " .:,;!?-_#"), ut.defer("split", "#")])

    def __init__(self, elastic):
        super().__init__(elastic)
        self.entry_resource = PaginatedResource(URL_TEMPLATE)
        # register a string-join function for the lxml XPath
        ns = etree.FunctionNamespace(None)
        ns["string-join"] = _string_join

    def find_entries(self, page):
        docs = []
        for entry in self.entry_path(page):
            doc = ut.SDA({}, "N/A")
            doc["metadata.url"] = self.doc_path(entry)
            doc["metadata.date"] = self.date_path(entry)
            doc["metadata.title"] = self.title_path(entry)
            doc["metadata.detail_url"] = self.detail_path(entry)
            docs.append(doc.a_dict)

        return docs

    def process_document(self, document, **kwargs):
        doc = ut.SDA(document)
        resp = self.url_fetcher(doc["metadata.detail_url"])
        tree = html.fromstring(resp.content)
        for entry in self.meta_path(tree):
            key = self.key_path(entry)
            value = self.value_path(entry)
            doc[f"metadata.{key}"] = value
