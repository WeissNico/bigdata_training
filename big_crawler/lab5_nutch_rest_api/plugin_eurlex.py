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

        if lst:
            acc += lst
        elif res:
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
    return without_rid_qid.replace(".", cwd)


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
            "age": dt.timedelta(days=3)
        }
        self.defaults.update(kwargs)
        # create a unique index on the url
        self.collection.create_index([("url", pymongo.ASCENDING)], unique=True)

    def retrieve_new_documents(self, age=None):
        """Retrieves new documents using the EURLex search.

        Checks documents until it reaches an given age.

        Args:
            age (datetime.timedelta): the age until how far the crawler should
                go into the past. Defaults to None (class default).

        Returns:
            int: the number of newly found documents
        """
        if age is None:
            age = self.defaults["age"]
        exp_date = dt.date.today() - age
        today = dt.datetime.combine(dt.date.today(), dt.time.min)

        entry_path = etree.XPath(
            """
            //table[@class = 'documentTable']/tbody/tr[
                count(
                    self::tr[td[@class = 'publicationTitle']] |
                    preceding-sibling::tr[td[@class= 'publicationTitle']]
                ) = $block]
            """)
        date_path = etree.XPath(
            """
            .//td[contains(@class, 'Metadata')]//li[not(@class) and
                 contains(text(), 'Datum') or contains(text(), 'Date')]/text()
            """)
        doc_path = etree.XPath(
            """
            .//td[contains(@class, 'Metadata')]
            //li[@class = 'directTextAccess']
            /a[contains(@href, 'PDF') or contains(@href, 'HTML')]/@href
            """)
        title_path = etree.XPath(
            """
            .//td[@class = 'publicationTitle']//a/strong/text()
            """)
        detail_path = etree.XPath(
            """
            .//td[@class = 'publicationTitle']//a/@href
            """)

        timestamp = int(round(time.time() * 1000))
        url_tmpl = ("https://eur-lex.europa.eu/search.html?lang=de&qid="
                    f"{timestamp}&type=quick&scope=EURLEX&sortOneOrder=desc"
                    "&sortOne=DD&locale=de&page={}")

        has_unseen_documents = True
        doc_count = 0
        page = 1

        while has_unseen_documents:
            search_url = url_tmpl.format(page)
            logging.info(f"Crawling page '{search_url}' (page {page})")
            res = _retry_connection(search_url, "get")
            html_string = res.content
            tree = html.fromstring(html_string)

            child = 0
            while True:
                child += 1
                entry = entry_path(tree, block=child)
                if not entry:
                    break

                date_string = _flat_map(date_path, entry)[0]
                match = re.search(r"([^:]+): (\d+\/\d+\/\d+)", date_string)

                doc_date = dt.datetime.min
                doc_date_kind = None
                if match:
                    doc_date = dt.datetime.strptime(match[2], "%d/%m/%Y")
                    doc_date_kind = match[1]
                link = _make_resource_path(_flat_map(doc_path, entry)[0],
                                           "https://eur-lex.europa.eu")
                detail = _make_resource_path(_flat_map(detail_path, entry)[0],
                                             "https://eur-lex.europa.eu")
                title = _flat_map(title_path, entry)[0]

                doc = {"url": link, "detail_url": detail, "date": doc_date,
                       "date_kind": doc_date_kind, "title": title,
                       "crawl_date": today}

                logging.debug(f"Document date: {doc_date.date()}, "
                              f"Expiration date: {exp_date}")
                if doc_date.date() <= exp_date:
                    has_unseen_documents = False
                    break
                res = self.collection.update_one({"url": link}, {"$set": doc},
                                                 upsert=True)
                if res.modified_count > 0:
                    logging.debug(f"Document inserted or modified {res!s}")
                doc_count += res.modified_count
            page += 1
        logging.info(f"Found {doc_count} new or potentially modified docs.")
        return doc_count

    def enrich_documents(self, age=None):
        """Extracts additional metadata, by following the document links.

        Finds additional valuable metadata on the pages.
        When a change occurred, marks the document as modified.

        Args:
            age (datetime.timedelta): how far into the past may a document be
                dated, to still be checked. Defaults to None (class default)
        Returns:
            int: the number of enriched documents.
        """
        if age is None:
            age = self.defaults["age"]
        today = dt.datetime.combine(dt.date.today(), dt.time.min)
        exp_date = today - age

        success_count = 0
        cursor = self.collection.find({"date": {"$gte": exp_date}})

        # extract additional metadata
        for index, document in enumerate(cursor):
            logging.info(f"Processing document number {index}...")

            res = _retry_connection(document["detail_url"], "get")

            tree = html.fromstring(res.content)
            doc_num_path = "//*[@id='content']/div/div[2]/div[1]/h2"
            document_num = (tree.xpath(doc_num_path)[0].text)
            title_path = "//*[@id='translatedTitle']/strong"
            title = tree.xpath(title_path)[0].text

            document['document_number'] = document_num
            document['title'] = title

            for div_index in [4, 5]:
                meta_path = (f"//*[@id='multilingualPoint']/div[{div_index}]/"
                             "div[2]/ul/li")
                meta = tree.xpath(meta_path)

                if meta:
                    for i in range(1, len(meta) + 1):
                        name, value = (tree.xpath(meta_path + f"[{i}]")[0]
                                       .text.split(': '))
                        document[name] = value

            linked_path = "//*[@id='documentView']/div[3]/div[2]/ul/li[4]/a"
            if (tree.xpath(linked_path)):
                linked_value = tree.xpath(linked_path)[0].attrib['href']
                document["linked_source"] = linked_value
            # update document in the database
            success_count += self._update_document(document)
        return success_count

    def _update_document(self, document):
        """Updates a document in the mongoDB and detect modifications.

        When new metadata is enriched, mark it as new, if there are further
        modifications, mark it as modified.

        Args:
            document (dict): the current document.

        Returns:
            int: the number of modified documents (1 or 0).
        """
        # create a new set of database update options
        update_opts = {"new": True}
        update_opts.update(document)
        result = self.collection.update_one({"_id": document["_id"]},
                                            {"$set": update_opts})
        # when this document already had the "new" flag, the document was
        # and there was another modification, mark it as modified
        if "new" in document and result.modified_count > 0:
            update_opts["new"] = False
            result = self.collection.update_one({"_id": document["_id"]},
                                                {"$set": update_opts})
        return result.modified_count
