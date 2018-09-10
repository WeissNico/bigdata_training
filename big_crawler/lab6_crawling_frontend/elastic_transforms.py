"""This module provides some simple tools, in order to produce the elastic,
searches from some keywords.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import re
import datetime as dt

import utility as ut

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
    "reading_time": lambda x: {
        "reading_time": {"stats": {
            "script": {
                "id": "reading_time",
                "params": ut.TIME_FACTORS,
            }
        }}
    }
}


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


SORT_KEYS = {
    "_default": lambda k, o, a: {k: {
        "order": o,
        "missing": "_last",
        "unmapped_type": "integer"
        }},
    "quantity": lambda k, o, a: {"quantity.words": {"order": o}},
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
        cur_context = {}
        # check whether this is a range key
        match = re.match(r"(.+)_(from|to)$", key)
        # skip "to" keys
        if match and match[2] == "from":
            f_range = {"gte": filters[key]}
            to_value = filters.get(f"{match[1]}_to", None)
            if to_value is not None:
                f_range["lte": to_value]
            cur_context = {
                "range": {
                    match[1]: f_range
                }
            }
        else:
            keyword = "term"
            if isinstance(filters[key], list):
                keyword = "terms"
            cur_context = {
                keyword: {key: filters[key]}
            }
        filter_context.append(cur_context)
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


def transform_agg_filters(aggregations):
    """Transforms the aggregations into a format that can be processed easily.

    The return format is as follows:
    `{"filter_name": ["value_1, "value_2", "value_3"],
      "filter_range": {"from": "value_from", "to": "value_to"}
     }`

    Args:
        aggregations (dict): the aggregations as returned by the _search.

    Returns:
        dict: the transformed dict as described above.
    """
    def _transform_agg(name, el):
        # check whether list or dict
        if el.get("buckets") is not None:
            acc = [{"count": e["doc_count"], "value": e["key"]}
                   for e in el["buckets"]]
        else:
            # get type from field_name
            from_val = el["min"]
            to_val = el["max"]

            if name == "date":
                # elastic saves in milliseconds... so divide by 1000
                from_val = dt.date.fromtimestamp(from_val/1000)
                to_val = dt.date.fromtimestamp(to_val/1000)

            acc = {"from": from_val, "to": to_val}
        return acc

    return {k: _transform_agg(k, v) for k, v in aggregations.items()}
