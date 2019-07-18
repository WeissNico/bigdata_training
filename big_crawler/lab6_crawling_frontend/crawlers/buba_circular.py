"""The Plugin for the EBA-webpage.

The idea is to use the documents yielded by the advanced search, when given no
keywords to search for. These documents are automatically ordered by
update-date. Which is nice.

The bundesbank needs some previous crawling step to fill the `state` of
it's url-template with a valid value.
This is performed using the buba_state_fetcher from buba_helper.py

Author: Johannes Mueller <j.mueller@reply.de>
"""
import datetime as dt
import logging
from crawlers.plugin import (BasePlugin, PaginatedResource, XPathResource)
from crawlers.buba_helper import buba_state_fetcher
import utility as ut

# this template maker has to be filled by a valid state, which is done using
# the helper BubaSearchTemplate, which fills the state tag.
URL_TEMPLATE = ("https://www.bundesbank.de/action/de/730314/bbksearch"
                "?state={state}"
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

    Example: '01.01.2010'
    Returns: date(2010,01,01)
    """
    return dt.datetime.strptime(date_string, "%d.%m.%Y")


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
        ".//span[contains(normalize-space(@class), 'teasable__date')]/text()",
        after=[ut.defer("__getitem__", 0),
               ut.defer("strip"),
               _convert_dates]
    )

    title_path = XPathResource(
        ".//div[contains(normalize-space(@class), 'teasable__title')]"
        "/div[contains(normalize-space(@class), 'h2')]"
        "/text()[normalize-space()]",
        after=[ut.defer("__getitem__", 0), ut.defer("strip")]
    )

    doc_path = XPathResource(
        ".//a[contains(normalize-space(@class), 'teasable__link')]/@href",
        after=[
            ut.defer("__getitem__", 0),
            ut.curry(_make_resource_path, cwd=CWD)
        ]
    )

    def __init__(self, elastic):
        super().__init__(elastic)
        pre_filled_url = buba_state_fetcher(URL_TEMPLATE)
        self.entry_resource = PaginatedResource(pre_filled_url, min_page=0)

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
            doc["metadata.date"] = date
            doc["metadata.url"] = self.doc_path(entry)
            docs.append(doc.a_dict)

        return docs

    def process_document(self, document, **kwargs):
        # this is a stub which does nothing, EBA does not deliver any
        # additional metadata, or a detail url. Therefore, just the docs are
        # considered.
        return document
