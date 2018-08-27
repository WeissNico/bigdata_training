"""Describes the config for a eurolex plugin."""
import re
import datetime as dt

_timestamp = int(round(dt.time.time() * 1000))
_date_regex = re.compile(r"(\d+\/\d+\/\d+)")


def _inf_integers(start, step=1):
    while True:
        yield start
        start += step


def _complete_link(link):
    if link[:2] == "./":
        return f"https://eur-lex.europa.eu/{link[2:]}"
    return link


def _extract_date(text):
    match = _date_regex.search(text)
    if match:
        return match[1]
    return None


NAME = "EurLex"

RETRIEVE_LINKS = {
    # use 'page' parameter for pagination
    "url_tmpl": ("https://eur-lex.europa.eu/search.html?lang=de&qid="
                 f"{_timestamp}&type=quick&scope=EURLEX&sortOneOrder=desc"
                 "&sortOne=DD&locale=en&page={page}"),
    "$each": {
        "$xpath": """//table[@class = 'documentTable']/tbody/tr[
                     count(
                        "self::tr[td[@class = 'publicationTitle']] |
                        "preceding-sibling::tr[td[@class= 'publicationTitle]]
                     ) = $block]""",
        "$args": {"block": _inf_integers(1)},
        "$do": {
            "pdf_link": {
                "$xpath": """//td[contains(@class, 'Metadata')]
                             //li[@class = 'directTextAccess]
                             /a[contains(@href, "PDF")/@href""",
                "$after": _complete_link,
                "$default": None
            },
            "url": {
                "$xpath": """//td[@class = 'publicationTitle')]//a/@href""",
                "$after": _complete_link,
                "$default": None
            },
            "title": {
                "$xpath": """//td[@class = 'publicationTitle')]//a/text()""",
                "$after": str,
                "$default": "No title"
            },
            "date": {
                "$xpath": """//td[contains(@class, 'Metadata')]
                             //li[not(@class) and contains(text(), 'Date')]
                             /text()""",
                "$after": _extract_date,
                "$default": dt.datetime.min
            }
        }
    }
}
