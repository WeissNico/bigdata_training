"""This module defines some basic utility functions, that need to be used
on the backend.

Author: Johannes Mueller <j.mueller@reply.de>
"""

import functools
import datetime as dt

ORDER_STATUS = {"open": 2, "waiting": 1, "finished": 0}
ORDER_IMPACT = {"high": 2, "medium": 1, "low": 0}


def _fw(func):
    """Stupid consumer for unused kwargs."""
    def _kw_consumer(**kwargs):
        return func
    return _kw_consumer


def _get_similarity(other_doc="0", **kwargs):
    """Function to extract the similarity.

    Args:
        other_doc (str): the id of the document for comparison.
        **kwargs (dict): kwargs that will be consumed silently.
    """
    def _similarity_access(doc):
        return safe_dict_access(doc, ["connections", other_doc, "similarity"])
    return _similarity_access


SORT_KEYS = {
    "date": _fw(lambda doc: doc["date"]),
    "type": _fw(lambda doc: doc["type"]),
    "impact": _fw(lambda doc: ORDER_IMPACT[doc["impact"]]),
    "category": _fw(lambda doc: doc["category"]),
    "source": _fw(lambda doc: doc["source"]),
    "document": _fw(lambda doc: doc["document"]),
    "change": _fw(lambda doc: doc["change"]["lines_added"]),
    "quantity": _fw(lambda doc: doc["quantity"]["words"]),
    "reading time": _fw(lambda doc: doc["reading_time"]),
    "similarity": _get_similarity,
    "status": _fw(lambda doc: ORDER_STATUS[doc["status"]])
}


TIME_FACTORS = {"FAQ": 0.9,
                "Article": 1.1,
                "Directive": 1.5,
                "Regulation": 1.6}


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
        end_date = from_date()
    else:
        end_date = incl_date + dt.timedelta(days=HALF_YEAR)
        if end_date > from_date():
            end_date = from_date()
    start_date = end_date - dt.timedelta(days=FULL_YEAR)
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
    step = dt.timedelta(days=1)
    if desc:
        step = dt.timedelta(days=-1)
        start, end = end, start
    cur_date = start
    while cur_date != end:
        yield cur_date
        cur_date += step
    yield end


def sort_documents(documents, sort_key=None, desc=True, **kwargs):
    """Sorts the documents given by a provided sort key.

    Uses the sort key mapping as defined in `utility.SORT_KEYS`.

    Args:
        documents (list): a list of documents to sort.
        sort_key (str): a string for sorting, as present in `utility.SORT_KEYS`
            Defaults to None, which will just return documents.
        desc (bool): whether the list should be descending or not.
        **kwargs (dict): keyword args, that might be consumed by the sortfunc.

    Returns:
        list: the documents in a returned fashion.
    """
    sort_func = SORT_KEYS.get(sort_key, None)

    if sort_func is None:
        return documents

    return sorted(documents, key=sort_func(**kwargs), reverse=desc)


def safe_dict_access(dictionary, keys, default=None):
    """Accesses a dict with arbitrary depth in a safe fashion.

    Args:
        dictionary (dict): the (nested) dictionary that should be accessed.
        keys (list): a list of keys, that should be accessed in the given
            order.
        default (any): the object, that should be returned, when no match is
            found. Defaults to None (careful, when None can be saved).

    Returns:
        object: the object saved at
            `dictionary[keys[0]][keys[1]]...[keys[n]]` or `default`.
    """
    if len(keys) == 0:
        raise ValueError("There needs to be at least one key given.")

    if keys[0] in dictionary:
        if len(keys) == 1:
            return dictionary[keys[0]]
        return safe_dict_access(dictionary[keys[0]], keys[1:], default)
    else:
        return default


def dict_construct(dictionary, mapping):
    """Creates a dict out of an old one, by accessing the keys in a safe way.

    If a mapping looks like: `{"key_new": (["key_1", "key_2", "key_3"], 0)}`
    the resulting dict will be structured as follows:
    `{"key_new": dictionary["key_1"]["key_2"]["key_3"]}`
    If one of the keys is not present, it will be mapped to `0` (as given in
    the tuple).

    Args:
        dictionary (dict): the (nested) dictionary that should be accessed.
        mapping (dict): the mapping describing how the translation should
            be processed. See description above.

    Returns:
        dict: a resulting new dict.
    """
    new_dict = {}
    for key, tupl in mapping.items():
        opt = safe_dict_access(dictionary, *tupl)
        new_dict[key] = opt
    return new_dict


def frequencies(some_list, key=None):
    """Returns the frequencies of unique items in a list.

    Args:
        some_list (list): a list of items.
        key (function): some function to access the objects on the list.
            Defaults to None, which means nothing should be done.

    Returns:
        dict: a dict mapping `key(unique item) => frequency`.
    """
    if key is not None:
        some_list = map(key, some_list)

    def _count_unique(acc, val):
        acc[val] = acc.get(val, 0) + 1
        return acc

    counts = functools.reduce(_count_unique, some_list, {})
    return counts


def from_date(a_date=None):
    """Returns a given date as a datetime.datetime, time set to 00:00:00.0000

    Args:
        a_date (datetime.date): some date, defaults to None, which equals
            today's date.
    Returns:
        datetime.datetime: todays date.
    """
    if a_date is None:
        a_date = dt.date.today()
    return dt.datetime.combine(a_date, dt.time.min)


def get_reading_time(doc):
    """Returns a reading time for a given number of lines.

    Args:
        doc (dict): the document in question.

    Returns:
        datetime.timedelta: the reading time.
    """
    type_factor = TIME_FACTORS.get(doc["type"], 1)
    return dt.timedelta(seconds=(2 * doc["quantity"]["lines"] * type_factor))


def add_reading_time(doc):
    """Adds the reading time to a document.

    THIS OPERATION UPDATES THE ORIGINAL DICT!

    Args:
        doc (dict): the document in question.

    Returns:
        dict: an updated document.
    """
    upd = {"reading_time": get_reading_time(doc)}
    doc.update(upd)
    return doc
