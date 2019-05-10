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

URL_TEMPLATE = ("https://www.bundesbank.de/action/de/730314/bbksearch?state=H4sIAAAAAAAAAG1PQWrDQBD7Splj8cG57rFQQ6G0h"
                "uQD67ViL53surPjgwn5e2ehDg30JmkkobnS9wrZyNEzNRRmnxL4bSSXVuaGxhxO24KdLn7Cx3oh1zZ09gFayF1vhiMr5JdoniZGV"
                "88v2-eiMac9P0ctPaS3GnKH9kE4qsQ02ZBDS7VRir5DrXYPe15mP0DNHJOvta_JDwwbe_Zc8J-jFxQwgt6tKqs5R6_oJF_ufxo_5"
                "b_smFm6CLYIDcNXyaJVtmkVPopPI0qg2w-BkjLgTAEAAA"
                "&query=&tfi-730318=&tfi-730324="
                "&dateFrom=&dateTo="
                "&hitsPerPageString=50"
                "&sort=bbksortdate+desc"
                "&pageNumString={page}")


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


# TODO: update XPath Resources: date_path, doc_path
class BubaCircularPlugin(BasePlugin):
    CWD = "https://www.bundesbank.de"
    """Directory to use when localizing the relative paths."""

    source_name = "Deutsche Bundesbank Rundschreiben"
    """Name that should be displayed as source."""

    entry_path = XPathResource(
        "//li[contains(normalize-space(@class), 'resultlist__item')]"
    )

    date_path = XPathResource(
        ".//span[contains(normalize-space(@class), 'teasable__date')]"
        "/text()",
        after=[ut.defer("__getitem__", 0), ut.defer("strip")]
    )
    title_path = XPathResource(
        ".//li[contains(normalize-space(@class), 'resultlist__item')]"
        "//div[contains(normalize-space(@class), 'teasable__title')]"
        "//div[contains(normalize-space(@class), 'h2')]/text()",
        after=[ut.defer("__getitem__", 0), ut.defer("strip")]
    )

    doc_path = XPathResource(
        ".//li[contains(normalize-space(@class), 'resultlist__item')]"
        "//div[contains(normalize-space(@class), 'teasable__main-info')]"
        "//a[1]/@href",
        after=[ut.defer("__getitem__", 0), ut.curry(_make_resource_path, cwd=CWD)]
    )

    def __init__(self, elastic):
        super().__init__(elastic)
        self.entry_resource = PaginatedResource(URL_TEMPLATE, min_page=0)

    def find_entries(self, page):
        docs = []
        for entry in self.entry_path(page):
            doc = ut.SDA({}, "N/A")
            title = self.title_path(entry)
            if not title:
                continue
            doc["metadata.title"] = title
            logging.info(f"Found document: {title}.")
            date = self.date_path(entry)
            doc["metadata.date_original"] = date
            doc["metadata.url"] = self.doc_path(entry)
            docs.append(doc.a_dict)

        return docs

    def process_document(self, document, **kwargs):
        # this is a stub which does nothing, EBA does not deliver any
        # additional metadata, or a detail url. Therefore, just the docs are
        # considered.
        return document
