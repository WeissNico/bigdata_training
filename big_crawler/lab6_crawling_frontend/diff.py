"""Provides some functions for creating a html-diff view between two texts.

It relies heavily on difflib and the function used most will be `get_diff`.

Author: Johannes Mueller <j.mueller@reply.de>
"""

import difflib
import re

CONTEXT_LINE_REGEX = r"^@@ ([+-])(\d+,)?(\d+) ([+-])(\d+,)?(\d+) @@\s*$"
IDENTIFIER_MAP = {"+ ": 2, "- ": 1, "  ": 0}


def _get_unified_diff(doc, other):
    """Simple wrapper method for getting the unified diff."""
    current_text = doc["text"].splitlines()
    former_text = other["text"].splitlines()

    return difflib.unified_diff(former_text, current_text)


def _get_diff(doc, other):
    """DEPRECATED
    Simple wrapper method for not repeating myself."""

    current_text = doc["text"].splitlines()
    former_text = other["text"].splitlines()

    return difflib.ndiff(current_text, former_text)


def _parse_context_line(line):
    """Parse the context line of the diff (the one that starts with @@).

    Returns a dict with the following structure:

    `{"+": {"start": 1, "length": 7},
      "-": {"start": 1, "length": 4}}`

    Args:
        line (str): the context_line.

    Returns:
        dict: a dict as specified above.
    """
    match = re.match(CONTEXT_LINE_REGEX, line)
    if match is None:
        raise ValueError(f"The line: '{line}' seems to be no context line!")
    groupings = []
    for group in match.groups():
        if group in ["+", "-"]:
            groupings.append([group])
        elif group[-1] == ",":
            groupings[-1].append(int(group[:-1]))
        else:
            groupings[-1].append(int(group))

    for g in groupings:
        if len(g) < 3:
            g.append(1)
    ret = {g[0]: {"start": g[1], "length": g[2]} for g in groupings}
    return ret


def _not(sign):
    """Little utility, to reverse a sign."""
    if sign == "+":
        return "-"
    return "+"


def _process_unified_diff(deltas):
    """Process a unified diff to get a well-processable output.

    The output will be a list of blocks, where each block is represented by a
    dict. The dict-keys stand for the two versions '+' (right) and '-' (left).
    The values of these versions are arrays in the following format:

    `[{"num": 1, "mark": "highlight", "line": "text of first line"},
      {"num": 2, "mark": "highlight", "line": "text of second line"},
      {"num": '.', "mark": "crossout", "line": ""},
      {"num": '.', "mark": "crossout", "line": ""},
      {"num": '.', "mark": "crossout", "line": ""},
      {"num": 3, "mark": "", "line": "text of third line"}]`

    Args:
        deltas (str): the lines of the context diff.

    Returns:
        tuple: a list of dicts in the given format and a dict holding the
            changes.
    """
    blocks = []
    line_nums = {"+": 0, "-": 0}
    change = {"+": 0, "-": 0}
    cur_dict = None

    # skip the first two lines that contain +++ and --- respectively
    next(deltas)
    next(deltas)

    for d in deltas:
        if d[0] == "@":
            # a new block was found, create a new tuple
            if cur_dict is not None:
                blocks.append(cur_dict)
            cur_dict = {"+": [], "-": []}
            for s, vals in _parse_context_line(d).items():
                line_nums[s] = vals["start"]
        if d[0] == " ":
            for s in ["+", "-"]:
                # do it for both files.
                line_nums[s] += 1
                cur_dict[s].append({"num": line_nums[s], "mark": "",
                                    "line": d[1:]})
        elif d[0] in ["+", "-"]:
            s = d[0]
            line_nums[s] += 1
            change[s] += 1
            cur_dict[s].append({"num": line_nums[s], "mark": "highlight",
                                "line": d[1:]})
            cur_dict[_not(s)].append({"num": 0, "mark": "crossout",
                                      "line": " "})
    return blocks, change


def get_diff(doc, other):
    """DEPRECATED
    Creates a diff-list between two documents in the following format.

    `[{"type": 0, "line": "line in both documents"},
      {"type": 1, "line": "line only in first document"},
      {"type": 2, "line": "line only in second document"}]`

    Args:
        doc (dict): the new document whose text should be compared.
            (lines can only be added)
        other (dict): the older version of the documents.
            (lines can only be removed)

    Returns:
        list: a list as shown in the example.
    """
    diffs = _get_diff(doc, other)
    ret = []

    for line in diffs:
        identifier = line[:2]
        line_text = line[2:]
        line_type = IDENTIFIER_MAP.get(identifier, None)

        if line_type is None:
            continue

        ret.append({"type": line_type, "line": line_text})
    return ret


def get_diff_texts(doc, other):
    """DEPRECATED
    Creates two diff texts, returned as a tuple.

    Each tuple entry is an array in the following format:

    `[{"num": 1, "mark": True, "line": "text of first line"},
      {"num": 2, "mark": True, "line": "text of second line"},
      {"num": 0, "mark": False, "line": ""},
      {"num": 0, "mark": False, "line": ""},
      {"num": 0, "mark": False, "line": ""},
      {"num": 3, "mark": False, "line": "text of third line"}]`

    Returns:
        tuple: a tuple as described above.
    """
    diffs = get_diff(doc, other)
    ret = ([], [])
    line_counters = [0, 0]

    for line in diffs:
        if line["type"] == 0:
            for i in range(2):
                # do it for both files.
                line_counters[i] += 1
                ret[i].append({"num": line_counters[i], "mark": "",
                               "line": line["line"]})
        else:
            cur = line["type"]
            line_counters[cur-1] += 1
            ret[cur-1].append({"num": line_counters[cur-1],
                               "mark": "highlight",
                               "line": line["line"]})
            ret[cur % 2].append({"num": 0,
                                 "mark": "crossout",
                                 "line": " "})
    return ret


def get_unified_diff(doc, other):
    """Return a unified diff as a well-processable output.

    The output will be a list of blocks, where each block is represented by a
    dict. The dict-keys stand for the two versions '+' (right) and '-' (left).
    The values of these versions are arrays in the following format:

    `[{"num": 1, "mark": "highlight", "line": "text of first line"},
      {"num": 2, "mark": "highlight", "line": "text of second line"},
      {"num": '.', "mark": "crossout", "line": ""},
      {"num": '.', "mark": "crossout", "line": ""},
      {"num": '.', "mark": "crossout", "line": ""},
      {"num": 3, "mark": "", "line": "text of third line"}]`

    Args:
        doc (dict): the left document of this comparison.
        other (dict): the right document of this comparison.

    Returns:
        tuple: a list of dicts in the given format, and a dict of changes.
    """
    deltas = _get_unified_diff(doc, other)
    return _process_unified_diff(deltas)
