"""The Plugin for the EBA-webpage.

The idea is to use the documents yielded by the advanced search, when given no
keywords to search for. These documents are automatically ordered by
update-date. Which is nice.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import datetime as dt
import re
import logging


from crawlers.plugin import (BasePlugin, PaginatedResource, XPathResource)

import utility as ut


URL_TEMPLATE = ("https://eba.europa.eu/search"
                "?p_p_id=ebasearch_WAR_ebasearchportlet"
                "&_ebasearch_WAR_ebasearchportlet_keywords="
                "&_ebasearch_WAR_ebasearchportlet_language={locale}"
                "&_ebasearch_WAR_ebasearchportlet_contentType=document"
                "&_ebasearch_WAR_ebasearchportlet_doSearch=true"
                "&_ebasearch_WAR_ebasearchportlet_delta=200"
                "&_ebasearch_WAR_ebasearchportlet_resetCur=false"
                "&cur={page}")


def _make_resource_path(path, cwd):
    """Takes a relative `path` and a `cwd` and returns an absolute path.

    Args:
        path (str): the relative path (containing '.' and '.')
        cwd (str): the current working directory, to root the paths.

    Returns:
        str: a new absolute path
    """
    # TODO make more general.
    if path.startswith("/"):
        return f"{cwd}{path}"
    return path.replace(".", cwd)


def _convert_dates(date_string):
    """Converts the date from a given date string-span:

    Example: 'Publication date: 28/02/2019 (Last update: 04/03/2019)'
    Returns: {'Publication date': date(2019,02,28),
              'Last update': date(2019, 03, 04)}
    """
    match = re.findall(r"([\s\w]+): (\d{2}/\d{2}/\d{4})", date_string)

    if match:
        doc_dates = {m[0]: dt.datetime.strptime(m[1], "%d/%m/%Y")
                     for m in match}
    return doc_dates


class EBAPlugin(BasePlugin):

    CWD = "https://eba.europa.eu"
    """Directory to use when localizing the relative paths."""

    source_name = "EBA"
    """Name that should be displayed as source."""

    entry_path = XPathResource(
        "//tr[contains(normalize-space(@class), 'results-row')]/td[1]"
    )
    date_path = XPathResource(
        ".//span[contains(normalize-space(@class), 'result-date')]/text()",
        after=[ut.defer("__getitem__", 0), ut.defer("strip"), _convert_dates]
    )
    title_path = XPathResource(
        """
        ./div[contains(normalize-space(@class), 'search-result-title')]
         /a[1]/text()
        """,
        after=[ut.defer("__getitem__", 0), ut.defer("strip")]
    )
    doc_path = XPathResource(
        """
        ./div[contains(normalize-space(@class), 'search-result-title')]
         /a[1]/@href
        """,
        after=[ut.defer("__getitem__", 0),
               ut.curry(_make_resource_path, cwd=CWD)])

    def __init__(self, elastic):
        super().__init__(elastic)
        self.entry_resource = PaginatedResource(URL_TEMPLATE)

    def find_entries(self, page):
        docs = []
        for entry in self.entry_path(page):
            doc = ut.SDA({}, "N/A")
            title = self.title_path(entry)
            if not title:
                continue
            doc["metadata.title"] = title
            logging.info(f"Found document: {title}.")
            dates = self.date_path(entry)
            doc["metadata.date"] = dates.get("Last update", dt.datetime.now())
            doc["metadata.date_original"] = dates.get("Publication date",
                                                      dt.datetime.now())
            doc["metadata.url"] = self.doc_path(entry)
            docs.append(doc.a_dict)

        return docs

    def process_document(self, document, **kwargs):
        # this is a stub which does nothing, EBA does not deliver any
        # additional metadata, or a detail url. Therefore, just the docs are
        # considered.
        return document
