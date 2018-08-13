"""This module aims to provide some simple mock functions for creating
some objects too feed our frontend with.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import random
import calendar
from collections import OrderedDict
from datetime import date, timedelta

import utility as ut

TYPES = ["Regulation", "Guideline", "Directive", "FAQ", "Article"]
IMPACTS = ["high", "medium", "low"]
CATEGORIES = ["Securities", "Risk management", "General", "?"]
SOURCES = ["Inhouse",
           "https://eur-lex.europa.eu/legal-content/de/txt/",
           "https://voeb.de/download/",
           ("https://bafin.de/DE/PublikationenDaten/Jahresbericht/"
            "Jahresbericht/2016/Kapitel2/"),
           "https://bafin.de/sharedDocs/Veroeffentlichungen/DE",
           "https://bis.org/veroeffentlichungen/download/"]
DOCUMENTS = ["Anwendung der Richtlinie 2007/64/EG im operativen Geschäft",
             ("Änderungen im Verfahren durch Inkraftsetzung der Richtlinie "
              "(EU) 2015/2366"),
             ("RICHTLINIE (EU) 2015/2366 DES EUROPÄISCHEN PARLAMENTS UND DES "
              "RATES vom 25. November 2015 über Zahlungsdienste im Binnenmarkt"
              ", zur Änderung der Richtlinien 2002/65/EG, 2009/110/EG und "
              "2013/36/EU und der Verordnung (EU) Nr. 1093/2010 sowie zur "
              "Aufhebung der Richtlinie 2007/64/EG"),
             ("RICHTLINIE 2007/64/EG DES EUROPÄISCHEN PARLAMENTS UND DES RATES"
              " vom 13. November 2007 über Zahlungsdienste im Binnenmarkt, zur"
              " Änderung der Richtlinien 97/7/EG, 2002/65/EG, 2005/60/EG und "
              " 2006/48/EG sowie zur Aufhebung der Richtlinie 97/5/EG"),
             ("Entwurf Mindestanforderungen an die Sicherheit von "
              "Internetzahlungen, Konsultation 02/2015"),
             ("Fragen und Antworten zu den Mindestanforderungen an die "
              "Sicherheit von Internetzahlungen (MaSI)"),
             ("VERORDNUNG (EU) Nr. 575/2013 DES EUROPÄISCHEN PARLAMENTS UND "
              "DES RATES vom 26. Juni 2013 über Aufsichtsanforderungen an "
              "Kreditinstitute und Wertpapierfirmen und zur Änderung der "
              "Verordnung (EU) Nr. 646/2012"),
             ("Principles for effective risk data aggregation and risk "
              "reporting")]
STATUS = ["open", "waiting", "finished"]

MOCK_MEMORY_DB = OrderedDict()


def set_seed(cur_date):
    """Helper function to set the seed to a date, for consistency."""
    random.seed(cur_date)


def get_documents(cur_date):
    """Returns all mockuments for the given date.

    Args:
        cur_date (datetime.date): the current date

    Returns:
        list: a list of documents for the given date
    """
    return [doc for doc in MOCK_MEMORY_DB.values()
            if doc["date"] == cur_date]


def get_document(doc_id):
    """Returns a mockument with a given id.

    Args:
        doc_id (int): the documents id.

    Returns:
        dict: a saved document, if existant.
    """
    doc = MOCK_MEMORY_DB.get(doc_id, None)
    return doc


def set_document(doc_id, doc):
    """Sets a mockument to a given id.

    Args:
        doc_id (int): the documents id.
        doc (dict): the new document.
    """
    MOCK_MEMORY_DB[int(doc_id)] = doc


def create_random_date(year=None, month=None, min_date=None, max_date=None):
    """Creates a random date using the provided constraints.

    Args:
        year (int): which year this date should be placed in.
            Defaults to None.
        month (int): which month this date should be placed in.
            Defaults to None.
        min_date (datetime.date): the minimum age this date should become.
            Defaults to None, which equals one year before today.
        max_date (datetime.date): the maximum date this date should become.
            Defaults to None, which equals now.

    Returns:
        datetime.date: a new random date.
    """
    if min_date is None:
        min_date = date.today() - timedelta(days=365)
    if max_date is None:
        max_date = date.today()
    if year is None:
        year = random.randint(min_date.year, max_date.year)
    elif 1970 > year > 2100:
        raise ValueError(f"Year should lie between 1970 and 2100, not {year}.")
    if month is None:
        month = random.randint(min_date.month, max_date.month)
    elif 1 > year > 12:
        raise ValueError(f"Month should lie between 1 and 12, not {month}.")

    day = random.randint(1, calendar.monthlen(year, month))
    return date(year, month, day)


def create_mock_date(cur_date, **kwargs):
    """Creates a mocked date object.

    Args:
        cur_date (datetime.date): the date this mock date is for
        **kwargs (dict): other keys, that should be updated in the final obj.

    Returns:
        dict: some mock date object.
    """
    mock_date = {
        "date": cur_date
    }
    # get mocked docs for this date
    docs = get_documents(cur_date)
    if docs:
        freqs = ut.frequencies(docs, key=lambda x: x["status"])
        for st in ["open", "waiting", "finished"]:
            mock_date[f"n_{st}"] = freqs.get(st, 0)
    else:
        for st in ["open", "waiting", "finished"]:
            mock_date[f"n_{st}"] = random.randint(0, 5)

    mock_date.update(kwargs)
    return mock_date


def create_mockument(cur_date, **kwargs):
    """Creates a mocked document, binding the given kw-args if necessary.

    Args:
        cur_date (datetime.date): the date this document should be created for
        **kwargs (dict): other keys, that should be updated in the final obj.

    Returns:
        dict: some mock document.
    """
    mod = random.choice((True, False))
    doc = {}
    # this works because of ordered dict
    new_id = "0"
    keys = list(MOCK_MEMORY_DB.keys())
    if keys:
        new_id = str(int(keys[-1]) + 1)
    doc["id"] = new_id
    doc["date"] = cur_date
    doc["new"] = not mod
    doc["type"] = random.choice(TYPES)
    doc["impact"] = random.choice(IMPACTS)
    doc["category"] = random.choice(CATEGORIES)
    doc["source"] = random.choice(SOURCES)
    doc["document"] = random.choice(DOCUMENTS)
    # create some quantity
    num_words = random.randint(100, 300000)
    num_lines = num_words // random.randint(10, 20)
    doc["quantity"] = {"lines": num_lines, "words": num_words}
    # create some change
    num_lines_rem = 0
    num_lines_add = num_lines
    if mod:
        num_lines_rem = random.randint(0, num_lines)
        num_lines_add = random.randint(0, num_lines)
    doc["change"] = {"lines_added": num_lines_add,
                     "lines_removed": num_lines_rem}
    doc["status"] = random.choice(STATUS)

    # put in the remaining kwargs
    doc.update(kwargs)
    # save to memory db
    MOCK_MEMORY_DB[new_id] = doc
    return doc


def get_or_create_documents(cur_date, num):
    """Returns all mockuments for the given date.

    If the desired number is not met, creates new documents.

    Args:
        cur_date (datetime.date): the current date
        num (int): the desired number of documents, defaults to None
            (no change if there are any documents, otherwise random 3-10).

    Returns:
        list: a list of documents for the given date
    """
    docs = get_documents(cur_date)
    if num is None:
        if len(docs) > 0:
            return docs
        else:
            num = random.randint(3, 10)
    diff = num - len(docs)
    if diff > 0:
        for i in range(diff):
            create_mockument(cur_date)
    return get_documents(cur_date)


def create_connected_documents(doc_id, num=None):
    """Creates a random number of connected documents, using all other docs.

    Args:
        doc_id (str): the current documents id.
        num (int): the number of random documents.
            Defaults to None, which means 1-20 documents.

    Returns:
        list: a list of connected documents, holding the keys:
            `[date, type, category, source, document, impact,
            number of references, quantity]`
    """
    if num is None:
        num = random.randint(1, 10)
    documents = []
    for i in range(1, num):
        new_doc = create_mockument(create_random_date())
        similarity = random.random() * 0.7 + 0.3
        new_doc["connections"] = {
            doc_id: {
                "doc_id": doc_id,
                "similarity": similarity
            }
        }
        documents.append(new_doc)
    return documents


def get_or_create_connected(doc_id):
    """Returns all connected documents or creates some mocked ones.

    Args:
        doc_id (int): the document whose connections should be found.

    Returns:
        list: a list of connected documents.
    """
    connected = [doc for doc in MOCK_MEMORY_DB.values()
                 if doc_id in ut.safe_dict_access(doc, ["connections"], [])]
    if not connected:
        return create_connected_documents(doc_id)
    return connected
