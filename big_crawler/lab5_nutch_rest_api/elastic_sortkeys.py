"""The only contained function is the transform_sortby function,
that transforms the given sort keyword (see the table-headers) into an
elasticsearch sort dict.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import utility as ut


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
                "lang": "painless",
                "source": "doc['quantity']['words'].value*params[doc['type']]",
                "params": ut.TIME_FACTORS,
            }
        },
        "order": o
    },
    "change": lambda k, o, a: {"change.lines_added": {
        "missing": 0,
        "order": o}},
    "similarity": lambda k, o, a: {
        "_script": {
            "type": "number",
            "script": {
                "lang": "painless",
                "source": "doc['fingerprint'].value - params.fingerprint",
                "fingerprint": a["fingerprint"]
            }
        },
        "order": o
    },
    "document": lambda k, o, a: {"title": {
        "order": o,
        "missing": "_last",
        "unmapped_type": "integer"
    }}
}


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
        return {}

    sorter = SORT_KEYS.get(sortby["keyword"], SORT_KEYS["_default"])
    return sorter(sortby["keyword"], sortby["order"], sortby["args"])
