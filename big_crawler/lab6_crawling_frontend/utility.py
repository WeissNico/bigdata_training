"""This module defines some basic utility functions, that need to be used
on the backend.

Author: Johannes Mueller <j.mueller@reply.de>
"""

import functools
import hashlib
import datetime as dt
import time
import re
import sys
import os

ORDER_STATUS = {"open": 2, "waiting": 1, "finished": 0}
ORDER_IMPACT = {"high": 2, "medium": 1, "low": 0}

PLATFORM = sys.platform

EXEC_SUFFIXES = {
    "win32": ".exe",
    "cygwin": ".exe",
    "linux": "",
    "darwin": ""
}


class _DefaultEntry():
    def __init__(self, contents):
        self.contents = contents

    def __call__(self, default=None):
        if self.contents is not None:
            return self.contents
        return default

    def also(self, override=None):
        if override is None:
            return self.contents
        return override


class DefaultDict():
    """Provides a easy way to access a dict of default values.

    Attributes can be used as key and are callable, taking a default value
    as argument.

    If the attribute can not be found, it returns `None`."""
    def __init__(self, a_dict, **kwargs):
        # catch problems, when a NoneInstance is given.
        if a_dict is None:
            a_dict = {}
        self.dict = dict(a_dict, **kwargs)

    def __getattr__(self, name):
        # check whether the attribute is defined on a dict.
        if hasattr(self.dict, name):
            return getattr(self.dict, name)
        # skip AttributeError and return a dictionary key or none.
        return _DefaultEntry(self.dict.get(name, None))

    # delegate subscriptability to dict.
    def __getitem__(self, key):
        return self.dict[key]

    def __contains__(self, key):
        return key in self.dict

    def __setitem__(self, key, value):
        self.dict[key] = value

    def other(self, dictionary):
        """Returns a combined dictionary, favors the new one."""
        return DefaultDict(self.dict, **dictionary)


class SDA:
    """Provides an easy way to access nested dicts by allowing dot-notation.

    Example:
        ```
        a = {"a": {"b": 1}}
        b = {"a": [{"b": 1}, {"b": 2}]}
        c = {"a": {"stupid.name": 1}}
        SDA(a)["a.b"]  # => 1
        SDA(a)["b.b"]  # => None
        SDA(b)["a.1.b"]  # => 2
        SDA(c)["a.stupid\.name"]  # => 1

        SDA(a)["a.c.d"] = "b"
        a  # {"a": {"b": 1, "c": {"d": "b"}}}
        ```
    """
    def __init__(self, a_dict=None, default=None, filler=None):
        """Initializes the safe dictionary.

        Args:
            a_dict (dict): the dictionary to wrap.
            default (any): the default value, that should be returned,
                when no value is found.
            filler (any): the default value, that should be put into
                lists when values are set.
        """
        self.regex = re.compile(r"(?<!\\)\.")
        self.a_dict = a_dict
        if self.a_dict is None:
            self.a_dict = {}
        self.default = default
        self.filler = filler or default

    def _process_keys(self, key):
        keys = self.regex.split(key)
        for i, k in enumerate(keys[:]):
            k = k.replace("\\", "")
            # try if these are a integer of float values.
            # (in this order, because a float might be converted to int)
            try:
                k = int(k)
            except ValueError as ve:
                try:
                    k = float(k)
                except ValueError as ve:
                    pass
            keys[i] = k

        return keys

    def setdefault(self, default):
        self.default = default

    # delegate most methods to the internal dict.
    def __getattr__(self, attr):
        return getattr(self.a_dict, attr)

    def __iter__(self):
        return (k for k in self.a_dict.keys())

    def __getitem__(self, key):
        keys = self._process_keys(key)
        return safe_dict_access(self.a_dict, keys, self.default)

    def __contains__(self, key):
        keys = self._process_keys(key)
        return safe_dict_has(self.a_dict, keys)

    def __setitem__(self, key, value):
        keys = self._process_keys(key)
        return safe_dict_write(self.a_dict, keys, value, self.filler)

    def __repr__(self):
        return repr(self.a_dict)


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


def _safe_set(dictionary, key, value, default=None):
    """Set a key in a dictionary or list alike."""
    try:
        dictionary[key] = value
    except IndexError:
        num = key - (len(dictionary) - 1)
        dictionary += [default] * num
        dictionary[key] = value


def _safe_get(dictionary, key, default=None):
    """Get a key in a dictionary or list alike."""
    ret = default
    try:
        ret = dictionary[key]
    except (KeyError, IndexError):
        pass
    return ret


def _safe_has(dictionary, key):
    """Returns whether a key is contained in a list or dictionary."""
    if isinstance(dictionary, (list, tuple)):
        return 0 <= key < len(dictionary)
    elif isinstance(dictionary, dict):
        return key in dictionary
    return False


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
    if _safe_has(dictionary, keys[0]):
        if len(keys) == 1:
            return dictionary[keys[0]]
        return safe_dict_access(dictionary[keys[0]], keys[1:], default)
    else:
        return default


def safe_dict_write(dictionary, keys, value, default=None):
    """Writes an entry to a nested dict of arbitrary depth.

    Args:
        dictionary (dict): the (nested) dictionary that should be accessed.
        keys (list): a list of keys, that should be accessed in the given
            order.
        value (any): the value that should be set.
        default (any): the value that should be set for empty dictionary
            entries.

    Returns:
        any: the value that was set.
    """
    if len(keys) == 0:
        raise ValueError("There needs to be at least one key given.")

    # break condition
    if len(keys) == 1:
        _safe_set(dictionary, keys[0], value, default)
        return value

    next_dict = _safe_get(dictionary, keys[0])
    if isinstance(next_dict, (list, tuple)):
        _safe_set(dictionary, keys[0], list(next_dict), default)
    elif not isinstance(next_dict, dict):
        _safe_set(dictionary, keys[0], {}, default),

    return safe_dict_write(dictionary[keys[0]], keys[1:], value, default)


def safe_dict_has(dictionary, keys):
    """Returns whether a sequence of keys exist in the given dictionary.

    Args:
        dictionary (dict): the (nested) dictionary that should be accessed.
        keys (list): a list of keys, that should be accessed in the given
            order.

    Returns:
        bool: whether this sequence of keys exists or not.
    """
    if len(keys) == 0:
        raise ValueError("There needs to be at least one key given.")

    # break condition
    if len(keys) == 1:
        return _safe_has(dictionary, keys[0])

    if _safe_has(dictionary, keys[0]):
        return safe_dict_has(dictionary[keys[0]], keys[1:])
    return False


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


def merge_dicts(*dictionaries):
    """Merges a list of dictionaries into one, using a recursive approach.

    Meaning, if a dictionary includes a nested dictionary, this will not be
    replaced by the merge dictionary.

    Example: ```
        merge_dicts({"a": {"b": 1}}, {"a": {"c": 2}})
        #  => {"a": {"b": 1, "c": 2}}
    ```

    Dictionaries defined first have a lower precedence (they will be
    overwritten by the dictionaries after).

    IMPORTANT: if a value is `None` it will not be used to overwrite a
    previously defined value. It will just insert it, when the key is
    undefined.

    Args:
        *dictionaries (list): a list of dicts that should be merged.
    """

    if len(dictionaries) == 0:
        raise IndexError("At least one dictionary is required!")
    elif len(dictionaries) == 1:
        return dictionaries[0]

    new_dict = dict(dictionaries[0])
    for other in dictionaries[1:]:
        for key in other.keys():
            cur_el = new_dict.get(key)
            if cur_el and isinstance(cur_el, dict):
                # if this is a dictionary call recursively
                new_dict[key] = merge_dicts(new_dict[key], other[key])
            # override only if the other value is not None
            elif other[key] is not None:
                new_dict[key] = other[key]
            # if it is none: override only if there is no value in the prev.
            # dictionaries
            elif other[key] is None and key not in new_dict:
                new_dict[key] = other[key]
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
    except (ValueError, IndexError, TypeError):
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


def update_existing(a_dict, other):
    """Updates a dictionaries values, but only if the key was present before.

    Args:
        a_dict (dict): a dictionary that should be updated.
        other (dict): the dictionary that contains new values for the keys.

    Example:
        ```
        a = {"b":3, "c": 2}
        b = {"a": 1, "b": 2, "c": 3}
        update_existing(a, b)  # => {"b":2, "c": 3}
        update_existing(b, a)  # => {"a": 1, b": 3, "c": 2}
        ```

    Returns:
        dict: the updated dictionary.
    """
    return {k: other.get(k, v) for k, v in a_dict.items()}


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


def noop(first, *args, **kwargs):
    """A function that returns the first argument and consumes arguments."""
    return first


def defer(func, *args, **kwargs):
    """A deferred function call.

    Args:
        func (str): the name of the function that should be called
        *args (list): the arguments that should be applied to the function.
        **kwargs (dict): the keyword arguments that should be applied to the
            function.

    Returns:
        callable: a function, which takes an object as argument and
            returns the item under the previously given key.
    """
    def _apply(obj):
        return getattr(obj, func)(*args, **kwargs)
    return _apply


def curry(func, *args, **kwargs):
    """A curried function call.

    Args:
        func (callable): the function that should be called with curried args.
        **kwargs (dict): the keyword arguments that should be applied to the
            function.

    Returns:
        callable: a function, which takes the remaining list of arguments as
            an input. Careful when considering argument order.
    """
    def _curried(*cargs, **cwargs):
        return func(*(args + cargs), **dict(cwargs, **kwargs))
    return _curried


def coerce_bool(expr):
    """Returns the boolean value of an expression, especially handling strings.

    Returns true for the strings: "true", "yes", "active", "on", "1".

    Args:
        expr (any): some expression.

    Returns:
        bool: whether the expression is truthy or not.
    """
    if isinstance(expr, str):
        return expr.lower() in {"true", "yes", "active", "on", "1"}
    return bool(expr)


def path_in_project(path, is_executable=False):
    """Returns the absolute path to a relative path in the project.

    If the option `is_executable` is provided, `path` becomes the filename and
    the function returns the absolute path to the executable.

    Args:
        path (str): Either a relative path in the project or the base name
            of an executable.
        is_executable (bool): when this option is given, `path` is treated like
            the base name of an executable file.

    Returns:
        str: a relative path to an executable.
    """
    base_dir = os.path.dirname(__file__)
    if not is_executable:
        return os.path.join(base_dir, path.strip("/\\"))
    # if this is an executable base name.
    if PLATFORM == "win32":
        return os.path.join(base_dir, "bin", PLATFORM,
                            path + EXEC_SUFFIXES[PLATFORM])
    else:
        return path + EXEC_SUFFIXES[PLATFORM]
