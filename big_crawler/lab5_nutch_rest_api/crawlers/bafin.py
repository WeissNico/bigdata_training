"""The Plugin for the BaFin-webpage.

The Idea is to use the rss feed as the source of news and and update
the database accordingly.

The connected files have to be considered recursively...

Author: Johannes Mueller <j.mueller@reply.de>
"""
import datetime as dt
import locale
import re

from lxml import etree, html

from crawlers.plugin import BasePlugin, PaginatedResource, XPathResource

import utility as ut


URL_TEMPLATE = ("https://www.bafin.de/SiteGlobals/Functions/Solr/Suche/"
                "Ergebnisdarstellung/Expertensuche/rssnewsfeed.xml"
                "?cms_input_=7844616"
                "&cms_gts=7855320_list%253DdateOfIssue_dt%252Bdesc"
                "&cms_gtp=7855320_list%253D{page}"
                "&https=1&cms_resourceId=7844738"
                "&cms_rss=rss"
                "&cms_language_={locale}&cms_pageLocale={locale}")


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
    """Converts the date from a given date string:

    Example `Fri, 23 Nov 2018 15:00:00 +0100`
    """
    match = re.search(r"\w{3}, (\d+ \w{3} \d{4} \d{2}:\d{2}:\d{2} [+-]\d{4})",
                      date_string)

    doc_date = dt.datetime.now()
    # date is given using english locale...
    locale.setlocale(locale.LC_TIME, "en_US")
    if match:
        doc_date = dt.datetime.strptime(match[1], "%d %b %Y %H:%M:S %z")
    locale.setlocale(locale.LC_TIME, "")
    return doc_date


class BafinPlugin(BasePlugin):

    CWD = "https://eur-lex.europa.eu"
    """Directory to use when localizing the relative paths."""

    source_name = "BaFin"
    """Name that should be displayed as source."""

    entry_path = XPathResource("//rss/channel/item")
    date_path = XPathResource(
        "./pubDate/text()",
        after=[ut.defer("__getitem__", 0), _convert_date]
    )
    doc_path = XPathResource(
        "./link/text()",
        after=[ut.defer("__getitem__", 0),
               ut.curry(_make_resource_path, cwd=CWD)]
    )
    title_path = XPathResource("./title/text()",
                               after=[ut.defer("__getitem__", 0)])
    detail_path = XPathResource("./link/text()",
                                after=[ut.defer("__getitem__", 0)])

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
