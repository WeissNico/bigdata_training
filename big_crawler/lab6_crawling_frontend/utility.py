"""This module defines some basic utility functions, that need to be used
on the backend.

Author: Johannes Mueller <j.mueller@reply.de>
"""

import functools
import hashlib
import datetime as dt
import time
import re

ORDER_STATUS = {"open": 2, "waiting": 1, "finished": 0}
ORDER_IMPACT = {"high": 2, "medium": 1, "low": 0}


class _DefaultEntry():
    def __init__(self, contents):
        self.contents = contents

    def __call__(self, default=None):
        if self.contents is not None:
            return self.contents
        return default


class DefaultDict():
    """Provides a easy way to access a dict of default values.

    Attributes can be used as key and are callable, taking a default value
    as argument.

    If the attribute can not be found, it returns `None`."""
    def __init__(self, a_dict):
        self.dict = a_dict

    def __getattr__(self, name):
        # skip internal values event when they're present in the dict.
        return _DefaultEntry(self.dict.get(name, None))

    def other(self, dictionary):
        """Returns a combined dictionary, favors the new one."""
        return DefaultDict(self.dict, **dictionary)


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
    "reading_time": _fw(lambda doc: doc["reading_time"]),
    "similarity": _get_similarity,
    "status": _fw(lambda doc: ORDER_STATUS[doc["status"]])
}


TIME_FACTORS = {
    "Announcement": 0.8,
    "FAQ": 0.9,
    "Article": 1.1,
    "Directive": 1.5,
    "Regulation": 1.6,
    "Guideline": 1.4,
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

    # check whether the key is in the dictionary
    has_member = keys[0] in dictionary
    # or whether the index lies in the length of the list.
    if isinstance(dictionary, (list, tuple)):
        has_member = len(dictionary) > keys[0] >= 0

    if has_member:
        if len(keys) == 1:
            return dictionary[keys[0]]
        return safe_dict_access(dictionary[keys[0]], keys[1:], default)
    else:
        return default


def try_keys(dictionary, keys, default=None):
    """Accesses a list of keys one after another, until a value is found.

    Accesses whether the key EXISTS, returns a default value, if all keys in
    the list are processed.

    Args:
        dictionary (dict): the dictionary that should be accessed.
        keys (list): a list of keys, that should be tried in the given
            order. Also allows nested keys. See `safe_dict_access`
        default (any): the object, that should be returned, when no match is
            found. Defaults to None (careful, when None can be saved).

    Returns:
        object: the object saved at
            `dictionary[keys[0]] or dictionary[keys[1]] or ... or default`
    """
    if len(keys) == 0:
        return default
    if keys[0] in dictionary:
        return dictionary[keys[0]]
    # check for nested keys, if there is no hit (None), be CAREFUL
    if isinstance(keys[0], (list, tuple)):
        obj = safe_dict_access(dictionary, keys[0])
        if obj is not None:
            return obj
    # recursive call using the tail
    return try_keys(dictionary, keys[1:], default)


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


def date_from_string(datestring):
    """Returs a date (as a datetime) from an isodate-string.

    Format example: `2018-09-10`

    Args:
        datestring (str): a date in string-format.

    Return:
        datetime.datetime: a valid python datetime.
    """
    if isinstance(datestring, (dt.date, dt.datetime)):
        return from_date(datestring)

    this_date = None
    try:
        this_date = dt.datetime.strptime(datestring[:10], "%Y-%m-%d")
    except ValueError:
        pass
    return from_date(this_date)


def calculate_reading_time(doc):
    """Returns a reading time for a given number of lines.

    Args:
        doc (dict): the document in question.

    Returns:
        datetime.timedelta: the reading time.
    """
    type_factor = TIME_FACTORS.get(doc["type"], 1)
    return dt.timedelta(seconds=(0.3 * doc["quantity"]["words"] * type_factor))


def calculate_quantity(text):
    """Returns the quantity of lines and words for a text.

    This is a stupid implementation that does not consider any textproperties.

    Args:
        text (str): the document's text in question.

    Returns:
        tuple: the numbers of lines and words.
    """
    lines = len(text.splitlines())
    words = len(re.split(r"\s+", text))
    return lines, words


def add_reading_time(doc):
    """Adds the reading time to a document.

    THIS OPERATION UPDATES THE ORIGINAL DICT!

    Args:
        doc (dict): the document in question.

    Returns:
        dict: an updated document.
    """
    upd = {"reading_time": calculate_reading_time(doc)}
    doc.update(upd)
    return doc


def add_quantity(doc):
    """Adds the reading time to a document.

    THIS OPERATION UPDATES THE ORIGINAL DICT!

    Args:
        doc (dict): the document in question.

    Returns:
        dict: an updated document.
    """
    lines, words = calculate_quantity(doc)
    upd = {
        "quantity": {
            "lines": lines,
            "words": words
        }
    }
    doc.update(upd)
    return doc


def filter_dict(dictionary, include=None, exclude=None):
    """Returns a dictionary (shallow), containing only the keys in filter_keys.

    Args:
        dictionary (dict): a python dict.
        include (list): the keys which should be included. Defaults to None,
            which means all keys should be included.
        exclude (list): the keys that should be excluded. Defaults to None,
            which means no keys should be excluded.
    Returns:
        dict: a filtered dictionary.
    """
    if include is None:
        include = list(dictionary.keys())

    if exclude is None:
        exclude = []

    return {k: v for k, v in dictionary.items()
            if k in include and k not in exclude}


def map_from_serialized_form(request_data):
    """Creates a map from the arguments provided by flasks request.args.

    Args:
        request_data (dict): the request parameters.

    Returns:
        dict: a dictionary holding the correct values in an easy to process
            format. Like `{"key_1": "value_1",
                           "key_2": ["value_2", "value_3", "value_4"],
                           "...", "..."}`
    """
    def _red_func(acc, el):
        if el["name"] in acc:
            if isinstance(acc["name"], list):
                acc[el["name"]].append(el["value"])
            else:
                acc[el["name"]] = [acc[el["name"]], el["value"]]
        else:
            acc[el["name"]] = el["value"]
        return acc

    return functools.reduce(_red_func, request_data, {})


def flatten_multi_dict(multi_dict):
    """Returns a flattened version of the given multidict.

    When only one value is present, returns a key value mapping, otherwise
    a ky, list of values mapping.

    Args:
        multidict werkzeug.MultiDict: a multi_dict instance

    Returns:
        dict: a dictionary holding the correct values in an easy to process
            format. Like `{"key_1": "value_1",
                           "key_2": ["value_2", "value_3", "value_4"],
                           "...", "..."}`
    """
    def _flatten(values):
        if len(values) == 0:
            return None,
        elif len(values) == 1:
            return values[0]
        else:
            return values

    deep_dict = multi_dict.to_dict(False)
    return {k: _flatten(v) for k, v in deep_dict.items()}


def convert_filter_types(dictionary):
    """Converts the string request types to their respective types.

    Returns:
        dict: the dictionary itself (operation happens inplace).
    """
    for key in dictionary.keys():
        if key.startswith("reading_time"):
            dictionary[key] = int(dictionary[key])
    return dictionary


def merge_filters(available_filters, active_filters):
    """Merges the available filters and the active filters into one dict.

    Args:
        available_filters (dict): all available filters as returned by elastic.
        active_filters (dict): all active filters as returned by elastic.

    Returns:
        dict: the merged dictionary of filters.
    """
    def _upsert_list(some_list, some_dict):
        for idx, entry in enumerate(some_list):
            if entry["value"] == some_dict["value"]:
                del some_list[idx]
        some_list.insert(0, some_dict)

    filters = {}
    for key in available_filters.keys():
        if key not in active_filters:
            filters[key] = available_filters[key]
            continue
        value = available_filters[key]
        if isinstance(value, dict):
            value["min"] = available_filters[key]["from"]
            value["max"] = available_filters[key]["to"]
            value["active"] = True
        else:
            for term in active_filters[key]:
                term["active"] = True
                _upsert_list(value, term)
        filters[key] = value
    return filters


def create_search_id(flask_app=None):
    """Creates a search id which is a hash using the secret key of the app.

    If no app is passed in, uses some standard unsecure id.

    Args:
        flask_app (Flask): the flask app, to pull the configuration from.
    """
    secret = "not a very good secret!"
    if flask_app is not None:
        secret = flask_app.config["SECRET_KEY"]
    sha_hasher = hashlib.sha256(f"{time.time()}.{secret}".encode("utf-8"))
    search_id = sha_hasher.hexdigest()
    return search_id


def get_base_url(url):
    """Returns the base domain of a url.

    Args:
        url (str): the full url.

    Returns:
        str: the base domain.
    """
    if url is None:
        return None
    # TODO make this smarter
    parts = url.split("/")
    relevant = [p for p in parts if "." in p]
    if len(relevant) > 0:
        return relevant[0]
    return parts[0]


def clean_value(some_value):
    """A simple utility function to return a cleaned value.

    If an empty list is given, returns None,
    if an empty dict is given, returns None,
    if None is given, returns None,
    if list or dict have just one value, this value is returned.

    Args:
        some_value (any): a simple value or an iterable.
    """
    try:
        length = len(some_value)
    except Exception:
        length = None

    if length is None:
        return some_value

    try:
        clean_list = list(some_value.values())
    except Exception:
        clean_list = list(some_value)

    if length == 0:
        return None
    if length == 1:
        return clean_list[0]

    return some_value
