"""This module provides the buba_state_fetcher function.

This function is used to fill the `state` attribute of a url-template with
a valid value.

Author: Johannes Mueller <j.mueller@reply.de>
"""
from urllib.parse import urlparse, urlunparse
from lxml import html
import string

from crawlers.plugin import _retry_connection, XPathResource
import utility as ut

# Define an XPath for the token:
state_xpath = XPathResource(
    "//form[@id = 'formSearchAction']/input[@name = 'state']/@value",
    after=[ut.defer("__getitem__", 0)]
)


def partial_string_format(template, *args, **kwargs):
    """This function partially replaces arguments in a template string.

    Arguments:
        template (str): a template string
        *args (list): the positional replacements passed to format().
            No effect on the partial logic, just here for completeness.
        **kwargs (dict): the keyword replacements passed to format().

    Returns:
        str: a preformatted template string
    """
    # build a dictionary for replacing all keys but state with their original
    # template.
    replace = {}
    for s in string.Formatter().parse(template):
        parts = ["{"]
        if not s[1]:
            continue
        if s[1] in kwargs:
            continue
        parts.append(s[1])
        # handle conversion
        if s[3]:
            parts.append(f"!{s[3]}")
        # handle spec
        if s[2]:
            parts.append(f":{s[2]}")
        parts.append("}")
        replace[s[1]] = "".join(parts)
    return template.format(*args, **kwargs, **replace)


def buba_state_fetcher(url_template, url_fetcher=None, **fetch_args):
    """Takes a URL_TEMPLATE and fills its `state={state}` query parameter.

    The parameter is obtained by calling the page without query parameters,
    retrieving the token and then returning it.

    Arguments:
        url_template (str): a template-string, which points to the bundesbank
            and has a {state} parameter.
        url_fetcher (callable): a callable taking a url as argument and returns
            a `requests.Response`. Defaults to plugin._retry_connection
        **fetch_args (dict): any keyword arguments that should be passed to the
            url_fetcher.

    Returns:
        str: the prefilled url-template.
    """
    # set default url_fetcher
    if url_fetcher is None:
        url_fetcher = _retry_connection
    # cut query from url
    url_wo_query = urlunparse((*urlparse(url_template)[:3], None, None, None))

    resp = url_fetcher(url_wo_query, **fetch_args)
    tree = html.fromstring(resp.content)

    # use xpath to get state
    state = state_xpath(tree)

    # return a partially formatted string
    return partial_string_format(url_template, state=state)
