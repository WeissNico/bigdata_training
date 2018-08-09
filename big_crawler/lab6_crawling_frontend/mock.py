"""This module aims to provide some simple mock functions for creating
some objects too feed our frontend with.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import random
from collections import OrderedDict

TYPES = ["Regulation", "Guideline", "Directive", "FAQ", "Article"]
IMPACTS = ["high", "medium", "low"]
CATEGORIES = ["Securities", "Risk management", "General", "?"]
SOURCES = ["Inhouse",
           "https://eur-lex.europa.eu/legal-content/de/txt/",
           "https://voeb.de/download/",
           "https://bafin.de/DE/PublikationenDaten/Jahresbericht/Jahresbericht/2016/Kapitel2/",
           "https://bafin.de/sharedDocs/Veroeffentlichungen/DE",
           "https://bis.org/veroeffentlichungen/download/"]
DOCUMENTS = ["Anwendung der Richtlinie 2007/64/EG im operativen Geschäft",
             "Änderungen im Verfahren durch Inkraftsetyung der Richtlinie (EU) 2015/2366",
             "RICHTLINIE (EU) 2015/2366 DES EUROPÄISCHEN PARLAMENTS UND DES RATES vom 25. November 2015 über Zahlungsdienste im Binnenmarkt, zur Änderung der Richtlinien 2002/65/EG, 2009/110/EG und 2013/36/EU und der Verordnung (EU) Nr. 1093/2010 sowie zur Aufhebung der Richtlinie 2007/64/EG",
             "RICHTLINIE 2007/64/EG DES EUROPÄISCHEN PARLAMENTS UND DES RATES vom 13. November 2007 über Zahlungsdienste im Binnenmarkt, zur Änderung der Richtlinien 97/7/EG, 2002/65/EG, 2005/60/EG und 2006/48/EG sowie zur Aufhebung der Richtlinie 97/5/EG",
             "Entwurf Mindestanforderungen an die Sicherheit von Internetzahlungen, Konsultation 02/2015",
             "Fragen und Antworten zu den Mindestanforderungen an die Sicherheit von Internetzahlungen (MaSI)",
             "VERORDNUNG (EU) Nr. 575/2013 DES EUROPÄISCHEN PARLAMENTS UND DES RATES vom 26. Juni 2013 über Aufsichtsanforderungen an Kreditinstitute und Wertpapierfirmen und zur Änderung der Verordnung (EU) Nr. 646/2012",
             "Principles for effective risk data aggregation and risk reporting"]
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
            if doc["date_id"] == cur_date.strftime("%Y-%m-%d")]


def get_document(doc_id):
    """Returns a mockument with a given id.

    Args:
        doc_id (int): the documents id.
    
    Returns:
        dict: a saved document, if existant.
    """
    doc = MOCK_MEMORY_DB.get(int(doc_id), None)
    return doc


def set_document(doc_id, doc):
    """Sets a mockument to a given id.

    Args:
        doc_id (int): the documents id.
        doc (dict): the new document.
    """
    MOCK_MEMORY_DB[int(doc_id)] = doc


def create_mock_date(cur_date, **kwargs):
    """Creates a mocked date object.
    
    Args:
        cur_date (datetime.date): the date this mock date is for
        **kwargs (dict): other keys, that should be updated in the final obj.
    
    Returns:
        dict: some mock date object.
    """
    doc = {
        "id": cur_date.strftime("%Y-%m-%d"),
        "display": cur_date.strftime("%d/%m/%Y"),
        "month": cur_date.strftime("%m-%Y"),
        "month_display": cur_date.strftime("%B %Y"),
        "n_open": random.randint(0, 5),
        "n_waiting": random.randint(0, 5), 
        "n_finished": random.randint(0, 5)
    }

    doc.update(kwargs)
    return doc


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
    new_id = 0
    keys = list(MOCK_MEMORY_DB.keys())
    if keys:
        new_id = keys[-1] + 1
    doc["id"] = new_id
    doc["date_id"] = cur_date.strftime("%Y-%m-%d")
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