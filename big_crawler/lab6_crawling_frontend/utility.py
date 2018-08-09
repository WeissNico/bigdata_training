"""This module defines some basic utility functions, that need to be used
on the backend.

Author: Johannes Mueller <j.mueller@reply.de>
"""

from datetime import date, timedelta

ORDER_STATUS = {"open": 2, "waiting": 1, "finished": 0}
ORDER_IMPACT = {"high": 2, "medium": 1, "low": 0}
SORT_KEYS = {
    "type": lambda doc: doc["type"],
    "impact": lambda doc: ORDER_IMPACT[doc["impact"]],
    "category": lambda doc: doc["category"],
    "source": lambda doc: doc["source"],
    "document": lambda doc: doc["document"],
    "change": lambda doc: doc["change"]["lines_added"],
    "quantity": lambda doc: doc["quantity"]["words"],
    "status": lambda doc: ORDER_STATUS[doc["status"]]
}


def get_year_range(incl_date=None):
    """Returns a tuple of a start date and an end date, around incl_date.

    Tries to balance the year around the `incl_date` but balances it in such a
    way, that the end date is never bigger than todays date.

    Args:
        incl_date (datetime.date): an included date. (defaults to None,
            which means the end date becomes todays date.
    
    Returns
        tuple(datetime.date, datetime.date): a start and end date, where start 
            is one year before the end date.
    """
    FULL_YEAR = 365
    HALF_YEAR = FULL_YEAR // 2

    if incl_date is None:
        end_date = date.today()
    else:
        end_date = incl_date + timedelta(days=HALF_YEAR)
        if end_date > date.today():
            end_date = date.today()
    start_date = end_date - timedelta(days=FULL_YEAR)
    return start_date, end_date
    

def generate_date_range(incl_date=None, desc=True):
    """Returns a generator from start to end-date for one year.

    If a date_string is given, tries to balance the year around the given date,
    otherwise picks the current_date as a start.
    
    Args:
        incl_date (datetime.date): an included date. (defaults to None)
        desc (bool): whether the generator should run in a descending or
            ascending order. (defaults to True)

    Yields:
        date: a date for each day for one year.
    """
    start, end = get_year_range(incl_date)
    step = timedelta(days=1)
    if desc:
        step = timedelta(days=-1)
        start, end = end, start
    cur_date = start
    while cur_date != end:
        yield cur_date
        cur_date += step
    yield end
    

def sort_documents(documents, sort_key=None, desc=True):
    """Sorts the documents given by a provided sort key.

    Uses the sort key mapping as defined in `utility.SORT_KEYS`.

    Args:
        documents (list): a list of documents to sort.
        sort_key (str): a string for sorting, as present in `utility.SORT_KEYS`
            Defaults to None, which will just return documents.
        desc (bool): whether the list should be descending or not.
    
    Returns:
        list: the documents in a returned fashion.
    """
    sort_func = SORT_KEYS.get(sort_key, None)

    if sort_func is None:
        return documents
    
    return sorted(documents, key=sort_func, reverse=desc)