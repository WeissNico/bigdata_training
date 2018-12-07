"""The Plugin for the google-webpage.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import datetime as dt
import re
from urllib.parse import quote_plus

from crawlers.plugin import BasePlugin, PaginatedResource, XPathResource

import utility as ut


URL_TEMPLATE = ("https://www.google.com/search?q={query}&hl={{locale}}"
                "&tbs={tp}&start={{page}}")
"""The template string for the PaginatedResource, page and locale escaped."""

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
              " (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36")

Q_SRC_TEMPLATE = "site:{src}"
Q_FT_TEMPLATE = "filetype:{ft}"
Q_TP_TEMPLATE = "qdr:{type}"
Q_TF_TEMPLATE = "cdr:1,cd_min:{from:%m/%d/%Y},cd_max:{to:%m/%d/%Y}"

Q_TYPE_HIERARCHY = {
    "c": 16,
    "": 8,
    "y": 4,
    "m": 2,
    "w": 1
}


def _convert_date(date_string):
    """Converts the date from a given DD.MM.YYYY string"""
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})", date_string)

    doc_date = dt.datetime.now()
    if match:
        doc_date = dt.datetime.strptime(match[1], "%d.%m.%Y")
    return doc_date


def _query_from_search(search):
    """Creates a query string and a tbs-value for the given search-dict."""
    s = ut.SDA(search)
    query = []
    query.append(s["keywords"])
    query.append(" OR ".join([Q_FT_TEMPLATE.format(ft=ft)
                              for ft in s["file_types"]]))
    query.append(" OR ".join([Q_SRC_TEMPLATE.format(src=src)
                              for src in s["sources"]]))

    tp = ""
    max_level = 0

    for cur_tp in s["time_periods"]:
        cur_level = Q_TYPE_HIERARCHY.get(cur_tp["type"], 0)
        if cur_level <= max_level:
            continue

        if cur_tp["type"] == "c":
            tp = Q_TF_TEMPLATE.format(**cur_tp)
        else:
            tp = Q_TP_TEMPLATE.format(**cur_tp)
        max_level = cur_level

    return {
        "query": quote_plus(" ".join(query)),
        "tp": quote_plus(tp)
    }


class SearchPlugin(BasePlugin):

    entry_path = XPathResource("//div[@class = 'g']")
    date_path = XPathResource(
        """
        .//div[@class = 's']/div/span[@class = 'st']/span[@class = 'f']/text()
        """,
        after=[ut.defer("__getitem__", 0), _convert_date]
    )
    doc_path = XPathResource(
        """
        .//div[@class = 'rc']/div[@class = 'r']/a/@href
        """,
        after=[ut.defer("__getitem__", 0)]
    )
    title_path = XPathResource(
        """
        .//div[@class = 'rc']/div[@class = 'r']/a/h3/text()
        """,
        after=[ut.defer("__getitem__", 0)]
    )

    def __init__(self, elastic, **search_args):
        super().__init__(elastic)
        search_id = search_args.get("search_id")
        search = self.elastic.get_search(search_id)

        self.entry_resource = PaginatedResource(
            URL_TEMPLATE.format(**_query_from_search(search)),
            min_page=0,
            page_step=10,
            headers={"User-Agent": USER_AGENT}
        )

    def find_entries(self, page):
        docs = []
        for entry in self.entry_path(page):
            doc = ut.SDA({}, "N/A")
            doc["metadata.url"] = self.doc_path(entry)
            doc["metadata.date"] = self.date_path(entry)
            doc["metadata.title"] = self.title_path(entry)
            doc["metadata.crawl_date"] = ut.from_date()
            docs.append(doc.a_dict)

        return docs

    def process_document(self, document, **kwargs):
        return document
