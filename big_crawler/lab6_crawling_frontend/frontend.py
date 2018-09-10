import logging
import io
import datetime as dt
import re

import elastic
from pymongo import MongoClient
from flask import (Flask, request, redirect, render_template, url_for,
                   send_file, jsonify)

import settings
import utility as ut
import mock as mck
import forms
import diff


logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config.from_object(settings)
# connect to the elasticDB
es = elastic.Elastic(app.config["ELASTICSEARCH_HOST"],
                     app.config["ELASTICSEARCH_PORT"],
                     (app.config["ELASTICSEARCH_USER"],
                      app.config["ELASTICSEARCH_PASSWORT"]),
                     docs_index="eur_lex")
# connect to the mongoDB
client = MongoClient("mongodb://159.122.175.139:30017")
db = client["crawler"]
mock = mck.Mocker(db.mockuments)


@app.route("/dashboard")
@app.route("/dashboard/<dbdate>")
def dashboard(dbdate=None):
    """The dashboard that greets the user every morning.
    Described in mockup/dashboard_first_draft.png

    Args:
        dbdate (str): date in isoformat, for which the dashboard should be
            displayed, defaults to None (today)

    Request Args:
        sortby (str): category to sort by, defaults to impact.
        desc (str): whether the search should be descending or ascending,
            defaults to 'True'.
    """
    if dbdate is None:
        db_date = ut.from_date()
    else:
        try:
            db_date = ut.from_date(dt.date.fromisoformat(dbdate))
        except ValueError as err:
            # when an invalid string is provided
            db_date = ut.from_date()

    # create mockuments :)
    mock.set_seed(db_date)
    documents = mock.get_or_create_documents(db_date, num=None)
    documents = [ut.add_reading_time(d) for d in documents]
    # create some mock calendar
    calendar = mock.get_or_create_calendar(db_date)
    cur_date = mock.get_or_create_date(db_date)

    # create sort order on the documents
    sort_by = request.args.get("sortby", "impact")
    desc = request.args.get("desc", "True").lower() == "true"

    documents = ut.sort_documents(documents, sort_key=sort_by, desc=desc)
    columns = ["impact", "type", "category", "", "document",
               "change", "reading_time", "status"]
    return render_template("dashboard.html",
                           calendar=calendar,
                           cur_date=cur_date,
                           documents=documents,
                           columntitles=columns,
                           types=sorted(mck.TYPES),
                           categories=sorted(mck.CATEGORIES),
                           sort_by=(sort_by, desc))


@app.route("/search", methods=["GET", "POST"])
@app.route("/search/<int:page>")
def search(page=1):
    """The non-dynamic document search with filtering options.

    The decision pro request parameters was found, since we want to provide
    portability of the links, which isn't possible with a session-like
    search ID.
    Also this keeps state out of play as long as possible.

    Args:
        search_id (str): a string which represents the current search
        page (int): the number of the pagination page to show.

    Request Args:
        q (str): the query string
        sortby (str): category to sort by, defaults to date.
        desc (str): whether the search should be descending or ascending,
            defaults to 'True'.
    """
    # create sort order for the documents
    sort_by = request.args.get("sortby", "impact")
    desc = request.args.get("desc", "True").lower() == "true"
    # retrieve filters and map them to a query.
    filters = ut.map_from_serialized_form(request.form)
    # retrieve search keyword
    query = request.args.get("q", "")
    sortby = {
        "keyword": sort_by,
        "order": "desc" if desc else "asc",
        "args": {"fingerprint": 12341234}
    }

    columns = ["date", "type", "category", "document", "source",
               "reading_time", "impact"]

    search_res = es.search_documents(query, page, columns, filters, sortby)

    # create a filter form
    FilterForm = forms.filter_form_factory(search_res["aggs"])
    fform = FilterForm()

    documents = search_res["results"]
    # convert the date
    for doc in documents:
        doc["date"] = ut.date_from_string(doc["date"])
        doc["reading_time"] = doc["reading_time"][0]

    return render_template("filtered_search.html",
                           filters=search_res["aggs"],
                           fform=fform,
                           documents=documents,
                           columntitles=columns,
                           page=page,
                           num_results=search_res["num_results"],
                           max_page=search_res["total_pages"],
                           q=query,
                           sort_by=(sort_by, desc),)


@app.route("/document/<doc_id>/download")
def document_download(doc_id):
    """Should return the document as saved in the database.

    Args:
        doc_id (str): the id of the document to reutrn.
    """
    doc = mock.get_document(doc_id)
    if doc and "content" in doc:
        return send_file(io.BytesIO(doc["content"]),
                         attachment_filename="source.pdf",
                         mimetype="application/pdf")
    return send_file("static/dummy.pdf")
    # right now, just sends some dummy pdf-file


@app.route("/document/<doc_id>/")
def document(doc_id):
    """Returns a documents detail view.

    Args:
        doc_id (str): the id of the document to reutrn.
    """
    doc = mock.get_document(doc_id)
    doc = ut.add_reading_time(doc)
    calendar = mock.get_or_create_calendar(doc["date"])
    cur_date = mock.get_or_create_date(doc["date"])
    versions = sorted(mock.get_or_create_versions(doc_id),
                      key=lambda x: x["date"], reverse=True)

    return render_template("document.html",
                           calendar=calendar,
                           cur_date=cur_date,
                           cur_doc=doc,
                           types=sorted(mck.TYPES),
                           categories=sorted(mck.CATEGORIES),
                           versions=versions)


@app.route("/document/<doc_id>/connections")
def document_connections(doc_id):
    """Shows the connections of the given document in a dashboard-view.

    Args:
        doc_id (str): the id of the document, whose connections should be
            displayed.

    Request Args:
        sortby (str): category to sort by, defaults to impact.
        desc (str): whether the search should be descending or ascending,
            defaults to 'True'.
    """
    doc = mock.get_document(doc_id)
    calendar = mock.get_or_create_calendar(doc["date"])
    cur_date = mock.get_or_create_date(doc["date"])
    connected = mock.get_or_create_connected(doc_id)
    connected = [ut.add_reading_time(d) for d in connected]

    # create sort order on the documents
    sort_by = request.args.get("sortby", "similarity")
    desc = request.args.get("desc", "True").lower() == "true"

    connected = ut.sort_documents(connected, sort_key=sort_by, desc=desc,
                                  other_doc=doc_id)

    doc["readingtime"] = ut.get_reading_time(doc)
    columns = ["date", "type", "document", "reading_time", "similarity"]

    return render_template("connections.html",
                           calendar=calendar,
                           cur_date=cur_date,
                           cur_doc=doc,
                           documents=connected,
                           columntitles=columns,
                           sort_by=(sort_by, desc))


@app.route("/document/<doc_id>/diff")
def document_diff(doc_id):
    """Displays the diff views for the given document.

    Provides a possibility to set the version of the document, to compare to.

    Args:
        doc_id (str): the id of the document, which should be compared
            to another.

    Request Args:
        compare_to (str): the id of the other document which should be in the
            comparison.
    """
    doc = mock.get_document(doc_id)
    calendar = mock.get_or_create_calendar(doc["date"])
    cur_date = mock.get_or_create_date(doc["date"])

    versions = sorted(mock.get_or_create_versions(doc_id),
                      key=lambda x: x["date"], reverse=True)
    # document needs to be reloaded...
    doc = mock.get_document(doc_id)
    compare_to = request.args.get("compare_to", None)
    other = None
    # when nothing is given for comparison, take the latest document
    if compare_to is None:
        other = versions[0]
    else:
        # otherwise get the one with the right id
        other = [d for d in versions if str(d["_id"]) == compare_to][0]
    diffs, change = diff.get_unified_diff(doc, other)

    return render_template("diff.html",
                           calendar=calendar,
                           cur_date=cur_date,
                           cur_doc=doc,
                           other_doc=other,
                           change=change,
                           versions=versions,
                           diff_texts=diffs)


@app.route("/document/<doc_id>/set_status", methods=["GET", "POST"])
def document_set_status(doc_id):
    """Should update the status of the document as saved in the database.

    Args:
        doc_id (str): the id of the document to return.

    Request Args:
        status (str): one of `open`, `waiting` or `finished`
    """
    doc = mock.get_document(doc_id)
    status = request.args.get("status", None)
    if status not in ["open", "waiting", "finished"]:
        return jsonify(success=False)
    doc["status"] = status
    mock.set_document(doc, doc_id)
    return jsonify(status=status, success=True)


@app.route("/document/<doc_id>/add_words", methods=["POST"])
def document_add_words(doc_id):
    """Adds new words to the document.

    Args:
        doc_id (str): the id of the document to reutrn.

    Request Args:
        words (list): a list of words that should be added.
            Count will be set to one
    """
    doc = mock.get_document(doc_id)
    words = request.get_json().get("words", None)
    for i, word in enumerate(words):
        # don't update words that already exist
        if word in doc["words"]:
            del words[i]
            continue
        doc["words"][word] = 1
    mock.set_document(doc_id, doc)
    return jsonify(words=words, success=True)


@app.route("/document/<doc_id>/remove_words", methods=["POST"])
def document_remove_words(doc_id):
    """Removes keywords from the document.

    Args:
        doc_id (str): the id of the document to return.

    Request Args:
        words (list): a list of words that should be removed.
    """
    doc = mock.get_document(doc_id)
    words = request.get_json().get("words", [])

    for i, word in enumerate(words):
        # don't remove words that do not exist
        if word not in doc["words"]:
            del words[i]
            continue
        del doc["words"][word]
    mock.set_document(doc_id, doc)
    return jsonify(words=words, success=True)


@app.route("/document/<doc_id>/set_properties", methods=["POST"])
def document_set_properties(doc_id):
    """Should update the properties of the document as saved in the database.

    Args:
        doc_id (str): the id of the document to return.

    Request Args:

    """
    doc = mock.get_document(doc_id)
    if doc is None:
        return jsonify(success=False)

    update = {}
    # TODO build a real filter pipeline.
    for item in request.get_json():
        if item["name"] not in doc:
            # don't allow keys, that weren't there.
            continue
        if item["name"] == "impact" and (item["value"] not in
                                         ["high", "medium", "low"]):
            continue
        elif item["name"] == "status" and (item["value"] not in
                                           ["open", "waiting", "finished"]):
            continue
        elif item["name"] in ["keywords", "entities"]:
            doc[item["name"]] = {key: doc[item["name"]].get(key, 1)
                                 for key in item["value"]}
        else:
            doc[item["name"]] = item["value"]
        update[item["name"]] = item["value"]
    mock.set_document(doc, doc_id)
    return jsonify(success=True, update=update)


@app.route("/searchdialog")
def searchdialog():
    """The search dialog as referenced in slides/FrontEndSearchOptions.pptx.

    It serves as a basis for the user to create new crawling jobs?
    """

    # mock some simple filetypes and time periods
    f_types = [{"id": "ft_pdf", "name": "pdf"},
               {"id": "ft_ppt", "name": "ppt"},
               {"id": "ft_csv", "name": "csv"},
               {"id": "ft_png", "name": "png"},
               {"id": "ft_jpg", "name": "jpg"},
               {"id": "ft_xls", "name": "xls"},
               {"id": "ft_xlsx", "name": "xlsx"}]
    t_periods = [{"id": "tp_last_week", "name": "Last week"},
                 {"id": "tp_last_month", "name": "Last month"},
                 {"id": "tp_last_year", "name": "Last year"},
                 {"id": "tp_older", "name": "Older than 1 year"}]
    sources = [{"id": "src_ezb",
                "name": "EZB",
                "link": "https://www.ecb.europa.eu/ecb/html/index.de.html"},
               {"id": "src_bb",
                "name": "Deutsche Bundesbank",
                "link": ("https://www.bundesbank.de/Navigation/DE/"
                         "Publikationen/publikationen.html")}]
    # render out the searchdialog template
    return render_template("searchdialog.html",
                           file_types=f_types,
                           time_periods=t_periods,
                           sources=sources)


@app.route("/create_new_search", methods=["POST"])
def create_new_search():
    """Receives the form of the search dialog an processes it accordingly."""
    # TODO
    return render_template("searchdialog.html")


@app.route("/train")
def train():
    doc_id = request.args.get('doc_id')
    if doc_id is None:
        return render_template('warning.html', warning="DocId is missing")
    else:
        url = '<iframe src="https://www.w3schools.com"></iframe>'
        return render_template('train.html', tags=["Tag1", "Tag2", "Tag4"],
                               url=url)


@app.route("/old_search")
def old_search():
    # get search keywords
    search_text = request.args.get("search", "")
    documents = es.search_documents(search_text)

    search_result = []
    for doc in documents:
        highlight = ut.dict_construct(doc, {
            "text": (["highlight", "text"], None),
            "tags": (["highlight", "tags"], None)
        })
        ret_doc = ut.dict_construct(doc, {
            "link": (["_source", "baseUrl"], "#"),
            "id": (["_id"], "no_id"),
            "filename": (["_source", "title"], "no title"),
            "date": (["_source", "metadata", "date"], "no date"),
            "text": (["_source", "text"], []),
            "tags": (["_source", "tags"], []),
        })

        # update the set keys for the search
        if (highlight["text"] is not None or highlight["tags"] is not None):
            if highlight["text"] is not None:
                ret_doc["text"] = highlight["text"]
            # shorten text
            ret_doc["text"] = ret_doc["text"][0][:200]
            logging.debug("Appending '{filename}': {tags}".format(**ret_doc))
            search_result.append(ret_doc)

    return render_template('search.html', results=search_result)


@app.route('/nutch')
def nutch():
    '''
    print("working, pleas wait")
    num_page = 1
    search_results = google.search("Geschäftsberichte Wacker 2016", num_page)
    print("done :)")

    return render_template('nutch.html', results=search_results)
    '''
    res = es.get_seeds()
    return render_template('seeds.html', seeds=res)


@app.route("/download")  # without endpoint an an AssertionError occurs
def download():
    doc_id = request.args.get('doc_id')
    if doc_id is None:
        return render_template('warning.html', warning="DocId is missing")
    else:
        return "Download should happen here"


@app.route("/")
def home():
    """The page that is anchored at '/'.

    For now, redirects to /dashboard.
    """
    return redirect(url_for("dashboard"))


@app.route("/removeTag", methods=['POST'])
def remove_tag():
    doc_id = request.form['doc_id']
    tag = request.form['tag']

    es.remove_tag(tag, doc_id)

    return "remove successfully"


@app.route("/addTag", methods=['POST'])
def add_tag():
    doc_id = request.form['doc_id']
    tag = request.form['tag']

    es.update_tag(tag, doc_id)

    return "update successfully"


@app.route("/addSeed", methods=['POST'])
def add_seed():
    category = request.form['category']
    url = request.form['url']
    name = request.form['name']
    doc_id = category + '#' + name

    seed = {
        "url": url,
        "name": name,
        "category": category,
        "doc_id": doc_id
    }

    es.set_seed(seed)

    return "update successfully"


@app.route("/deleteSeed", methods=['POST'])
def delete_seed():
    doc_id = request.form['doc_id']

    es.delete_seed(doc_id)

    return "delete successfully"


@app.template_global("url_pre")
def global_url_preserve(**update_params):
    """Returns a url for the current site, using the current request params.

    It provides functionality to update the given parameters (request or url)

    Args:
        **update_params (dict): keyword parameters that should be updated.
    Returns:
        str: a fitting url.
    """
    endpoint = request.endpoint
    params = request.view_args
    query_params = request.args

    params.update(query_params)
    params.update(update_params)

    return url_for(endpoint, **params)


@app.template_filter("str")
def filter_str(obj):
    """A str filter for the jinja2 templates.

    Args:
        number (int): the number.

    Returns:
        str: the stringified object.

    """
    return str(obj)


@app.template_filter("pluralize")
def filter_pluralize(number, singular="", plural="s"):
    """ A pluralize filter for the jinja2 templates.

    Args:
        number (int): the number.

    Returns:
        str: the given plural ending for the given number form.

    """
    if number == 1:
        return singular
    else:
        return plural


@app.template_filter("pair")
def filter_pair(value):
    """A filter for jinja2 templates, that makes a tuple out of a single value.

    It simply duplicates the given word, if it is a single value,
    if it already is a tuple, return the tuple.

    Args:
        value (any): object that should be duplicated.

    Returns:
        tuple: a tuple either `(value, value)` or simply `value`.
    """
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return tuple(value)

    return (value, value)


@app.template_filter("dflt")
def filter_default(value, default):
    """A filter for jinja2 templates, that returns a default value.

    If the value is falsy, returns the default value.

    Args:
        value (any): object that should be checked.
        default (any): default value for that object.

    Returns:
        any: `default` or `value`.
    """
    if value:
        return value
    return default


@app.template_filter("titlecase")
def filter_titlecase(sentence, separator=" "):
    """A titlecase filter for the jinja2 templates.

    The standard "title" doesn't quite cut it.

    Args:
        sentence (str): the word or words that should be titlecased.
        separator (str): the string that should be used,
            to rejoin the sentence.

    Returns:
        str: the sentenced with all words in titlecase.
    """
    def _titlecase(word):
        if word in special:
            return word
        else:
            return word[:1].upper() + word[1:]

    special = ["the", "of", "in", "on", "at", "from", "a", "an"]

    return separator.join([_titlecase(p)
                           for p in re.split(r"[ _-]", sentence)])


@app.template_filter("ccase")
def _proxy_titlecase(sentence):
    tcase = filter_titlecase(sentence, "")
    return tcase[:1].lower() + tcase[1:]


@app.template_filter("bignumber")
def filter_bignumber(number):
    """A filter for the jinja2 templates, printing big numbers in format.

    Args:
        number (number): some big number.

    Returns:
        str: a formatted number
    """
    if number >= 1000000:
        return f"{number/1000000:.1f} M"
    elif number >= 1000:
        return f"{number/1000:.1f} K"
    else:
        return f"{number}"


@app.template_filter("bigminutes")
def filter_bigminutes(seconds):
    """A filter for the jinja2 templates, printing big time units in format.

    This should also work when given a `datetime.timedelta`
    Args:
        seconds (int): some number of seconds.

    Returns:
        str: a formatted number
    """
    if isinstance(seconds, dt.timedelta):
        minutes = seconds.total_seconds() // 60
    else:
        minutes = seconds // 60

    if minutes == 0:
        return "< 01 m"
    hours, mins = divmod(minutes, 60)
    return f"{hours:02.0f} h {mins:02.0f} m"


@app.template_filter("sign")
def filter_sign(number):
    """A filter for the jinja2 templates, printing just the sign of a number.

    Args:
        number (number): some number.

    Returns:
        str: either '+' or '-' dependent on the number.
    """
    if number < 0:
        return "-"
    return "+"


@app.template_filter("decimalnumber")
def filter_decimal(number, places=2):
    """A filter for the jinja2 templates, printing decimal numbers in format.

    Args:
        number (number): some big number.
        places (int): number of places after the comma, defaults to 2.

    Returns:
        str: a formatted number
    """
    return f"{number:.{places}f}"


@app.template_filter("domainextract")
def filter_domainextract(domain):
    """Extracts the domain name of a complex link.

    Returns the word if domain is not a link.

    Args:
        domain (str): some link.

    Returns:
        str: the base domain.
    """
    # TODO make this not stupid :)
    parts = domain.split("/")
    relevant = [p for p in parts if "." in p]
    if len(relevant) > 0:
        return relevant[0]
    return parts[0]


@app.template_filter("isodate")
def filter_isodate(some_date):
    """Returns the ISO date format of a given date.

    Args:
        some_date (datetime.date): the given date object.

    Returns:
        str: the ISO date (YYYY-MM-DD)
    """
    ret = "no date"
    try:
        ret = some_date.strftime("%Y-%m-%d")
    # when a non-valid string was passed
    except AttributeError:
        pass
    return ret


@app.template_filter("engldate")
def filter_engldate(some_date):
    """Returns the english date format of a given date.

    Args:
        some_date (datetime.date): the given date object.

    Returns:
        str: the english date (DD/MM/YYYY)
    """
    ret = "no date found"
    try:
        ret = some_date.strftime("%d/%m/%Y")
    # when a non-valid string was passed
    except AttributeError:
        pass
    return ret


@app.template_filter("isomonth")
def filter_isomonth(some_date):
    """Returns the ISO month format of a given date.

    Args:
        some_date (datetime.date): the given date object.

    Returns:
        str: the ISO month (YYYY-MM)
    """
    ret = "no month"
    try:
        ret = some_date.strftime("%Y-%m")
    # when a non-valid string was passed
    except AttributeError:
        pass
    return ret


@app.template_filter("displaymonth")
def filter_displaymonth(some_date):
    """Returns a human readable english month format of a given date.

    Args:
        some_date (datetime.date): the given date object.

    Returns:
        str: the english date (Month YYYY)
    """
    return some_date.strftime("%B %Y")


@app.template_filter("from")
def filter_from(number, minimum=0, maximum=1):
    """Returns a dict holding the clip number, it's minimum and it's maximum.

    Args:
        number (float): the number to assess.
        minimum (float): the minimum value for the number.
        maximum (float): the maximum value for the number.

    Returns:
        dict: a dict with the keys: `number`, `minimum` and `maximum`.
    """
    ret = {
        "minimum": minimum,
        "maximum": maximum
    }
    if number < minimum:
        ret["number"] = minimum
    elif number > maximum:
        ret["number"] = maximum
    else:
        ret["number"] = number
    return ret


@app.template_filter("to")
def filter_to(obj, start_or_list, end=None):
    """Returns a dict holding the clip number, it's minimum and it's maximum.

    Args:
        obj (dict): a dict holding a number, and it's range, as returned by
            `from`.
        start_or_list (int or list): either a number, as start of a range,
            or an iterable.
        end (int): the end of a range (included).

    Returns:
        object: the object onto which the `obj["number"]` was mapped.
    """
    mapping = start_or_list
    if end is not None:
        mapping = list(range(start_or_list, end + 1))

    delta = obj["maximum"] - obj["minimum"]
    length = len(mapping)
    baskets = [obj["minimum"] + (i+1) * (delta/length) for i in range(length)]

    for basket, mapped in zip(baskets, mapping):
        if obj["number"] < basket:
            return mapped
    # this case should normally not match, but just in case...
    return mapping[-1]


@app.template_filter("clip")
def filter_clip(num, lower, upper):
    """Returns the given number clipped to the range lower - upper,

    Args:
        num (number): the number that should be clipped to the given range
        lower (number): the lower bound of the number range.
        upper (number): the upper bound of the number range.

    Returns:
        number: the given number clipped to the range.
    """
    if num < lower:
        return lower
    elif num > upper:
        return upper
    return num


if __name__ == "__main__":
    # app = create_app(config.DATABASE_URI, debug=True)
    app.debug = True
    app.run(host="0.0.0.0", port="80")
