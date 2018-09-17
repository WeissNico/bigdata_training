import time
import logging
import re
import datetime as dt
from functools import reduce

import pymongo
import requests
from lxml import etree, html


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
                logging.info(f"Try to {method} to '{url}'.")
                response = s.request(method, url, **kwargs)
        except requests.exceptions.ConnectionError as connErr:
            # sleep increasing (exponential time intervals)
            logging.info("Detected an Error while connecting... "
                         f"retry ({retry})")
            time.sleep(2 ** retry)
    return response


def _make_resource_path(path, cwd):
    """Takes a relative `path` and a `cwd` and returns an absolute  path.

    Also cuts away the unnecessary `rid` and `qid` attributes.

    Args:
        path (str): the relative path (containing '.')
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


class EurlexPlugin():
    def __init__(self, mongo_collection, **kwargs):
        """Initializes a new EURLex-plugin, using the given `mongo_collection`.

        The results will be saved in the given `mongo_collection`.

        Args:
            mongo_collection (pymongo.collection.Collection): target collection
            **kwargs (dict): keyword arguments to update the class defaults.

        Returns:
            EurlexPlugin: initializes a new instance of the EurlexPlugin.
        """
        self.collection = mongo_collection
        self.defaults = {
            "age": dt.timedelta(days=3),
            "mongo_version": [3, 6, 0, 0]
        }
        self.defaults.update(kwargs)
        # create a unique index on the url
        self.collection.create_index([("url", pymongo.ASCENDING)], unique=True)
        # register a string-join function for the lxml XPath
        ns = etree.FunctionNamespace(None)
        ns["string-join"] = _string_join

    def retrieve_new_documents(self, limit=100):
        """Retrieves new documents using the EURLex search.

        Checks documents until it reaches a given limit.

        Args:
            limit (int): the maximium number of documents that should be
                retrieved.

        Returns:
            int: the number of newly found documents
        """
        today = dt.datetime.combine(dt.date.today(), dt.time.min)

        entry_path = etree.XPath("//div[@class = 'SearchResult']")
        date_path = etree.XPath(
            """
            .//dl/dd[preceding-sibling::dt[contains(text(), 'Date') or
                                           contains(text(), 'Datum')]]/text()
            """)
        doc_path = etree.XPath(
            """
            .//ul[contains(@class, 'SearchResultDoc')]/li
            /a[contains(@href, 'PDF') or contains(@href, 'HTML')]/@href
            """)
        title_path = etree.XPath(".//h2/a[@class = 'title']/text()")
        detail_path = etree.XPath(".//h2/a[@class = 'title']/@href")

        timestamp = int(round(time.time() * 1000))
        url_tmpl = ("https://eur-lex.europa.eu/search.html?lang=de&qid="
                    f"{timestamp}&type=quick&scope=EURLEX&sortOneOrder=desc"
                    "&sortOne=DD&locale=de&page={}")

        has_unseen_documents = True
        doc_count = 0
        page = 1

        while (doc_count < limit) and has_unseen_documents:
            search_url = url_tmpl.format(page)
            logging.info(f"Crawling page '{search_url}' (page {page})")
            res = _retry_connection(search_url, "get")
            html_string = res.content
            tree = html.fromstring(html_string)

            for entry in entry_path(tree):
                if not isinstance(entry, list):
                    entry = [entry]

                date_string = _flat_map(date_path, entry)[0]
                match = re.search(r"(\d+\/\d+\/\d+)", date_string)

                doc_date = dt.datetime.min
                if match:
                    doc_date = dt.datetime.strptime(match[1], "%d/%m/%Y")
                if len(_flat_map(doc_path, entry)) == 0:
                    continue
                link = _make_resource_path(_flat_map(doc_path, entry)[0],
                                           "https://eur-lex.europa.eu")
                detail = _make_resource_path(_flat_map(detail_path, entry)[0],
                                             "https://eur-lex.europa.eu")
                title = _flat_map(title_path, entry)[0]

                doc = {"url": link, "detail_url": detail, "date": doc_date,
                       "title": title, "crawl_date": today}

                logging.debug(f"Document date: {doc_date.date()}")

                num_docs = self.collection.count_documents({"url": link})

                if num_docs > 0:
                    logging.debug(f"Document was crawled before: '{link}'")
                    # check whether this document had a date before the crawl
                    # date, if not, break.
                    duplicate_doc = self.collection.find_one({"url": link})

                    if duplicate_doc["date"] >= duplicate_doc["crawl_date"]:
                        logging.debug("Document date lies in the future."
                                      " Continue...")
                        continue

                    logging.debug("Break!")
                    has_unseen_documents = False
                    break

                res = self.collection.insert_one(doc)
                doc_count += 1
            page += 1
        logging.info(f"Found {doc_count} new or potentially modified docs.")
        return doc_count

    def enrich_documents(self, limit=100):
        """Extracts additional metadata, by following the document links.

        Finds additional valuable metadata on the pages.
        When a change occurred, marks the document as modified.

        Args:
            age (datetime.timedelta): how far into the past may a document be
                dated, to still be checked. Defaults to None (class default)
        Returns:
            int: the number of enriched documents.
        """
        entry_path = etree.XPath("//dl[contains(@class, 'NMetadata')]/dd")
        key_path = etree.XPath("normalize-space(./preceding-sibling::dt[1])")
        value_path = etree.XPath("""
            normalize-space(
                string-join(
                    ./text() | .//*[self::span[@lang] or
                                    self::a[not(child::span)] or
                                    self::i[not(child::span)]]/text(), "#"
                )
            )
            """)

        success_count = 0
        cursor = (self.collection.find({"metadata": {"$exists": False}})
                  # newest first, and limit by limit
                  .sort([("date", -1)]).limit(limit))
        # extract additional metadata
        for index, document in enumerate(cursor):
            logging.info(f"Processing document number {index}...")

            res = _retry_connection(document["detail_url"], "get")

            tree = html.fromstring(res.content)

            metadata = {}
            for idx, entry in enumerate(entry_path(tree)):
                key = key_path(entry).strip(" .:,;!?-_#")
                val = value_path(entry).strip(" .:,;!?-_#").split("#")
                if len(key) == 0 or key in metadata:
                    key += str(idx)
                if len(val) == 0:
                    continue
                metadata[key] = val

            document["metadata"] = metadata
            # update document in the database
            result = self.collection.update_one({"_id": document["_id"]},
                                                {"$set": document})
            success_count += result.modified_count
        return success_count
