"""This module provides some simple tools, in order to produce the elastic,
searches from some keywords.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import re
import datetime

import utility as ut

sda = ut.safe_dict_access


def _extract_tp(some_tp_id):
    """Try to extract the given dates from the time_period id.

    Returns standard values on failure.

    Args:
        some_tp_id (str): a time periods id, something like:
            `tp_2015-10-01_2015-12-01`.

    Returns:
        dict: a time range dict, holding from and to keys.
    """
    d_range = {
        "type": "c",
        "from": ut.from_date(datetime.datetime.min),
        "to": ut.from_date()
    }

    parts = some_tp_id.split("_")
    if len(parts) == 3:
        d_range["from"] = ut.date_from_string(parts[1])
        d_range["to"] = ut.date_from_string(parts[1])
    return d_range


OUTPUT_CONV = {
    "_default": lambda x: x,
    "reading_time": lambda x: x[0],
    "date": lambda x: ut.date_from_string(x)
}
"""Rules for converting fields into an easy processable format."""

TIME_PERIODS = {
    "_default": _extract_tp,
    "tp_last_week": lambda x: {
        "type": "w",
        "from": ut.from_date() - datetime.timedelta(days=7),
        "to": ut.from_date()
    },
    "tp_last_month": lambda x: {
        "type": "m",
        "from": ut.from_date() - datetime.timedelta(days=30),
        "to": ut.from_date()
    },
    "tp_last_year": lambda x: {
        "type": "y",
        "from": ut.from_date() - datetime.timedelta(days=365),
        "to": ut.from_date()
    },
    "tp_older": lambda x: {
        "type": "",
        "from": ut.from_date(datetime.datetime.min),
        "to": ut.from_date()
    }
}
"""Rules for converting the time period ids."""


SEARCH_CONV = {
    "_default": lambda x: x,
    "name": lambda x: x[0],
    "keywords": lambda x: x[0],
    "time_periods": lambda x: [
        TIME_PERIODS.get(it, TIME_PERIODS["_default"])(it) for it in x
    ]
}
"""Rules for converting the keys of a search dict."""

INPUT_CHECKS = {
    "_default": lambda x: False,
    "impact": lambda x: x in ["low", "medium", "high"],
    "status": lambda x: x in ["open", "waiting", "finished"],
    "document": lambda x: len(x) > 0,
    "date": lambda x: isinstance(x, datetime.datetime),
    "keywords": lambda x: isinstance(x, dict),
    "entities": lambda x: isinstance(x, dict),
    "type": lambda x: len(x) > 0,
    "category": lambda x: len(x) > 0
}
"""Checks whether a user input is valid."""

AGG_KEYS = {
    "_default": lambda x: {
        x: {"terms": {"field": x, "order": {"_count": "desc"}}},
    },
    "date": lambda x: {
        "date": {"stats": {"field": x}},
    },
    "quantity": lambda x: {
        "quantity": {"stats": {"field": "quantity.words"}},
    },
    "source": lambda x: {
        "source": {"terms": {"field": "source.name",
                             "order": {"_count": "desc"}}},
    },
    "reading_time": lambda x: {
        "reading_time": {"stats": {
            "script": {
                "id": "reading_time",
                "params": ut.TIME_FACTORS,
            }
        }}
    },
    # document is somehow no good filter, since the titles get very long
    # therefore deactivate it.
    "document": lambda x: {}
}
"""Special rules when aggregating fields. _default for the default."""


FILTER_KEYS = {
    "_default": lambda k, v, p: {
        p["keyword"]: {k: v}
    },
    "source": lambda k, v, p: {
        p["keyword"]: {"source.name": v}
    },
    "quantity_range": lambda k, v, p: {
        "range": {"quantity.words": p}
    },
    "reading_time_range": lambda k, v, p: {
        "script": {
            "script": {
                "id": "reading_time_range",
                # beautiful way to extend the dict.
                "params": dict(ut.TIME_FACTORS, **p)
            }
        }
    },
    "date_range": lambda k, v, p: {
        "range": {"date": p}
    }
}
"""Special rules when filtering for fields. `KEY_range` for range filters."""


SCRIPT_FIELDS = {
    "reading_time": lambda x: {
        "reading_time": {
            "script": {
                "id": "reading_time",
                "params": ut.TIME_FACTORS,
            }
        }
    }
}
"""Script fields, that should be included in the search results."""


SORT_KEYS = {
    "_default": lambda k, o, a: {
        k: {
            "order": o,
            "missing": "_last",
            "unmapped_type": "integer"
        }
    },
    "impact": lambda k, o, a: {
        "_script": {
            "type": "number",
            "script": {
                "id": "keyword_sort",
                "params": {
                    "_field": k,
                    "low": 0,
                    "medium": 1,
                    "high": 2,
                },
            },
            "order": o,
        },
    },
    "status": lambda k, o, a: {
        "_script": {
            "type": "number",
            "script": {
                "id": "keyword_sort",
                "params": {
                    "_field": k,
                    "open": 0,
                    "waiting": 1,
                    "finished": 2,
                },
            },
            "order": o,
        },
    },
    "quantity": lambda k, o, a: {"quantity.words": {"order": o}},
    "source": lambda k, o, a: {"source.name": {"order": o}},
    "reading_time": lambda k, o, a: {
        "_script": {
            "type": "number",
            "script": {
                "id": "reading_time",
                "params": ut.TIME_FACTORS,
            },
            "order": o
        },
    },
    "change": lambda k, o, a: {"change.lines_added": {
        "missing": 0,
        "order": o}},
    "similarity": lambda k, o, a: {
        "_script": {
            "type": "number",
            "script": {
                "id": "similarity",
                "params": a,
            }
        },
        "order": o
    },
}


def transform_aggs(fields):
    """Transforms a given list of fields into an elastic aggregation context.

    Args:
        fields (list): a list of field names, which should be aggregated.

    Returns:
        dict: a valid elasticsearch aggs-dictionary.
    """
    aggs = {}

    if fields is None:
        return aggs

    for field in fields:
        agg_func = AGG_KEYS.get(field, AGG_KEYS["_default"])
        agg_dict = agg_func(field)
        aggs.update(agg_dict)

    return aggs


def transform_fields(fields):
    """Transforms a given list of fields into _source and scripted fields.

    Returns a list and a dict, the first for the _source or None,
    the latter for scripted_fields.

    Args:
        fields (list): a list of field names, which should be transformed.

    Returns:
        tuple: a list of `_source` fields and a dict of `script_fields`
    """
    if fields is None:
        return None, None

    source = []
    scripts = {}

    for field in fields:
        if len(field) == 0:
            continue
        script = SCRIPT_FIELDS.get(field, None)
        if script is None:
            source.append(field)
        else:
            scripts.update(script(field))

    return source, scripts


def transform_filters(filters):
    """Transforms a given dict of filters into an elastic filter context.

    Args:
        filters (dict): consisting key value pairs, where each key corresponds
            to one value or a list of value.
            Range filters are indicated by keys ending in _from and _to.

    Returns:
        list: an elasticsearch filter context.
    """
    filter_context = []

    for key in filters.keys():
        # check whether this is a range key
        match = re.match(r"(.+)_(from|to)$", key)
        # skip "to" keys
        if match and match[2] == "to":
            continue

        params = {}
        values = filters[key]
        params["keyword"] = "term"
        if isinstance(values, list):
            params["keyword"] = "terms"
        # process "from" keys
        if match and match[2] == "from":
            del params["keyword"]
            params["gte"] = filters[key]
            to_value = filters.get(f"{match[1]}_to", None)
            if to_value is not None:
                params["lte"] = to_value
            # rename key
            key = f"{match[1]}_range"
        # retrieve rule
        rule = FILTER_KEYS.get(key, FILTER_KEYS["_default"])
        filter_context.append(rule(key, values, params))
    return filter_context


def transform_sortby(sortby):
    """Takes an sortby-dict and transforms it into a valid elasticsearch sort.

    Args:
        sortby (dict): consisting of keyword to sort after, as seen in the
            table headers, a sort order ('asc' or 'desc') and required args.
            EXAMPLE: `{"keyword": "impact", "order": "desc", "args": {}}`

    Returns:
        dict: an elasticsearch sort context.
    """
    if not sortby:
        return []

    sorter = SORT_KEYS.get(sortby["keyword"], SORT_KEYS["_default"])
    return [sorter(sortby["keyword"], sortby["order"], sortby["args"])]


def transform_calendar_aggs(aggregations):
    """Transforms the given aggregations into a simple calendar-date.

    CAREFUL ELASTICSEARCH JUST RETURNS ESTIMATES.

    Args:
        aggregations (dict): the aggregations as returned by the _search.

    Returns:
        list: the transformed aggregations as described above.
    """
    calendar = []
    for agg in sda(aggregations, ["dates", "buckets"], []):
        cur_date = {
            "date": ut.date_from_string(agg.get("key_as_string")),
            "n_open": 0,
            "n_waiting": 0,
            "n_finished": 0
        }
        for status in sda(agg, ["statusses", "buckets"], []):
            cur_date[f"n_{status['key']}"] = status["doc_count"]
        calendar.append(cur_date)
    return calendar


def transform_agg_filters(aggregations, active={}):
    """Transforms the aggregations into a format that can be processed easily.

    If the request.args are given an "active" field marks whether the filter
    is in use or not.
    The return format is as follows:
    `{"filter_name": ["value_1, "value_2", "value_3"],
      "filter_range": {"from": "value_from", "to": "value_to"}
     }`

    Args:
        aggregations (dict): the aggregations as returned by the _search.
        active (dict): the request_arguments, as passed to the filter_context.
            May be used to mark which filters are active and which not.

    Returns:
        dict: the transformed dict as described above.
    """
    def _transform_agg(name, el):
        # check whether list or dict
        acc = None
        if el.get("buckets") is not None:
            # check if there is any bucket in the list
            if not el["buckets"]:
                return acc
            acc = [{"count": e["doc_count"], "value": e["key"],
                    "active": e["key"] in active.get(name, {})}
                   for e in el["buckets"]]
        else:
            # get minimum and maximum value
            min_val = el.get("min")
            max_val = el.get("max")
            # if this is a date
            if "min_as_string" in el:
                min_val = el.get("min_as_string")[:10]
                max_val = el.get("max_as_string")[:10]

            if min_val is None or max_val is None:
                return acc

            acc = {"min": min_val, "max": max_val,
                   "active": (f"{name}_from" in active or
                              f"{name}_to" in active),
                   "from": active.get(f"{name}_from", min_val),
                   "to": active.get(f"{name}_to", max_val)}
        return acc

    if aggregations is None:
        return {}
    return {k: _transform_agg(k, v) for k, v in aggregations.items()}


def _transform_document(doc):
    """Transforms a single resulting document in a well-processable form."""
    # append all source fields + run OUTPUT_CONVerters
    ret = {k: OUTPUT_CONV.get(k, OUTPUT_CONV["_default"])(v)
           for k, v in doc.get("_source", {}).items()}
    # append id field
    ret["_id"] = doc.get("_id", None)
    # append all other fields + run OUTPUT_CONVerters
    ret.update({k: OUTPUT_CONV.get(k, OUTPUT_CONV["_default"])(v)
                for k, v in doc.get("fields", {}).items()})
    return ret


def transform_output(results):
    """Transforms the results dictionary into an easy readable document list.

    Args:
        results (dict): the results of a elastic_search operation.

    Returns:
        list: a list of cleaned documents.
    """
    res = ut.SDA(results)

    if res["_source"]:
        return _transform_document(results)
    if res["hits.total"] > 0:
        return [_transform_document(doc) for doc in res["hits.hits"]]
    # otherwise
    return []


def transform_input(update):
    """Transforms the given update-dict into a valid update body.

    Args:
        update (dict): the properties and the values that should be updated.

    Returns:
        dict: a filtered and cleaned update dictionary.
    """
    filtered = {}
    for k, v in update.items():
        check = INPUT_CHECKS.get(k, INPUT_CHECKS["_default"])
        if check(v):
            filtered[k] = v

    return filtered


def transform_search(search):
    """Prepares a search dict for inserting it into the database.

    Args:
        search (dict): the search, as retrieved from the POST.

    Returns:
        dict: a nicely prepared dictionary for insertion.
    """
    trans = {k: SEARCH_CONV.get(k, SEARCH_CONV["_default"])(v)
             for k, v in search.items()}

    return trans


def check_dict(dictionary, allowed=None, required=None):
    """Transforms and checks a dictionary.

    Args:
        dictionary (dict): the dictionary, that should be inspected.
        allowed (list): a list of keys that are allowed, hence, others will
            be excluded. defaults to None, which allows all keys.
        required (list): a list of keys that are required, returns an error,
            when these are not present.

    Returns:
        dict: the processed dictionary.

    Raises:
        KeyError
    """
    clean_dict = {}
    errors = []
    for k in dictionary:
        if k in allowed:
            clean_dict[k] = dictionary[k]
    for k in required:
        if not clean_dict.get(k):
            errors.append(k)

    if errors:
        raise(KeyError("Couldn't find values for the following keys: "
                       + ", ".join(errors)))
