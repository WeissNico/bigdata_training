from datetime import date

from flask import (Flask, request, redirect, render_template, url_for,
                   send_file, jsonify)

from elasticsearch import Elasticsearch, RequestsHttpConnection
from settings import (ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORT,
                      ELASTICSEARCH_HOST, ELASTICSEARCH_PORT)

from elastic import Elastic
import utility
import mock


es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
app = Flask(__name__)
elastic = Elastic()


@app.route("/search", methods=['GET', 'POST'])
def search():
    # get search keywords
    search_text = request.args.get('search')
    auth = (ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORT)
    es = Elasticsearch(host=ELASTICSEARCH_HOST,
                       port=ELASTICSEARCH_PORT,
                       connection_class=RequestsHttpConnection,
                       use_ssl=True,
                       timeout=220,
                       max_retries=10, retry_on_timeout=True,
                       http_auth=auth)
    # res = requests.get(ELASTIC_URL+"/=")
    s_body = {"query": {"simple_query_string": {"query": search_text}},
              "highlight": {"fields": {"*": {"pre_tags": ["<b>"],
                                             "post_tags": ["</b>"]}}}}
    results = es.search(index="testcase", body=s_body)
    data = [doc for doc in results['hits']['hits']]

    search_result = list()
    for doc in data:
        text = utility.safe_dict_access(doc, ["highlight", "text"], None)
        hl_tags = utility.safe_dict_access(doc, ["highlight", "tags"], None)
        if (text is not None or hl_tags is not None):
            link = utility.safe_dict_access(doc, ["_source", "baseUrl"])
            id = utility.safe_dict_access(doc, ["_id"], "no id")
            filename = utility.safe_dict_access(doc, ["_source", "title"],
                                                None)
            if not filename:
                filename = "no title"
            date = utility.safe_dict_access(doc,
                                            ["_source", "metadata", "date"],
                                            "no date")
            if text is None:
                text = utility.safe_dict_access(doc, ["_source", "text"],
                                                "no text")
            # shorten text
            text = text[0][:200]
            tags = utility.safe_dict_access(doc, ["_source", "tags"], [])
            print(f"{filename}) {tags}")

            search_result.append({'id': id, 'filename': filename, 'date': date,
                                  'text': text, 'tags': tags, 'link': link})

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
    res = elastic.get_seeds()
    return render_template('seeds.html', seeds=res)


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
        db_date = date.today()
    else:
        try:
            db_date = date.fromisoformat(dbdate)
        except ValueError as err:
            # when an invalid string is provided
            db_date = date.today()

    # create mockuments :)
    mock.set_seed(db_date)
    documents = mock.get_or_create_documents(db_date, num=None)
    cur_date = mock.create_mock_date(db_date)
    # create some mock calendar
    calendar = [mock.create_mock_date(d)
                for d in utility.generate_date_range(db_date)]

    # create sort order on the documents
    sort_by = request.args.get("sortby", "impact")
    desc = request.args.get("desc", "True").lower() == "true"

    documents = utility.sort_documents(documents, sort_key=sort_by, desc=desc)
    columns = ["impact", "type", "category", "", "document", "change",
               "quantity", "status"]
    return render_template("dashboard.html",
                           calendar=calendar,
                           cur_date=cur_date,
                           documents=documents,
                           columntitles=columns,
                           sort_by=(sort_by, desc))


@app.route("/document/<doc_id>/download")
def document_download(doc_id):
    """Should return the document as saved in the database.

    Args:
        doc_id (str): the id of the document to reutrn.
    """
    # right now, just sends some dummy pdf-file
    return send_file("static/dummy.pdf")


@app.route("/document/<doc_id>/")
def document(doc_id):
    """Returns a documents detail view.

    Args:
        doc_id (str): the id of the document to reutrn.
    """
    return render_template("document.html")


@app.route("/document/<doc_id>/set_status")
def document_set_status(doc_id):
    """Should update the status of the document as saved in the database.

    Args:
        doc_id (str): the id of the document to reutrn.

    Request Args:
        status (str): one of `open`, `waiting` or `finished`
    """
    doc = mock.get_document(doc_id)
    status = request.args.get("status", None)
    if status not in ["open", "waiting", "finished"]:
        return jsonify(success=False)
    doc["status"] = status
    mock.set_document(doc_id, doc)
    return jsonify(status=status, success=True)


@app.route("/document/set_properties")
def document_set_properties():
    """Should update the properties of the document as saved in the database.

    Request Args:
        docId (str): the documents id, required.
        impact (str): the impact of the document.
        type (str): the type of the document.
        category (str): the category of the document.
    """
    doc_id = request.args.get("id", None)
    if doc_id is None:
        return jsonify(success=False)
    doc = mock.get_document(doc_id)
    update = {}
    for item in request.args.items():
        if item[0] not in doc:
            # don't allow keys, that weren't there.
            continue
        if doc[item[0]] == item[1]:
            continue
        if item[0] == "impact" and item[1] not in ["high", "medium", "low"]:
            continue
        doc[item[0]] = item[1]
        update[item[0]] = item[1]
    mock.set_document(doc_id, doc)
    return jsonify(success=True, update=update)


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
    cur_date = mock.create_mock_date(doc["date"])
    calendar = [mock.create_mock_date(d)
                for d in utility.generate_date_range(doc["date"])]
    connected = mock.get_or_create_connected(doc_id)

    # create sort order on the documents
    sort_by = request.args.get("sortby", "similarity")
    desc = request.args.get("desc", "True").lower() == "true"

    connected = utility.sort_documents(connected, sort_key=sort_by, desc=desc,
                                       other_doc=doc_id)
    columns = ["date", "type", "document", "quantity", "similarity"]

    return render_template("connections.html",
                           calendar=calendar,
                           cur_date=cur_date,
                           cur_doc=doc,
                           documents=connected,
                           columntitles=columns,
                           sort_by=(sort_by, desc))


@app.route("/searchdialog")
def searchdialog():
    """The search dialog as referenced in slides/FrontEndSearchOptions.pptx."""

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


@app.route("/new_search", methods=["POST"])
def new_search():
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

    elastic.remove_tag(tag, doc_id)

    return "remove successfully"


@app.route("/addTag", methods=['POST'])
def add_tag():
    doc_id = request.form['doc_id']
    tag = request.form['tag']

    elastic.update_tag(tag, doc_id)

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

    elastic.set_seed(seed)

    return "update successfully"


@app.route("/deleteSeed", methods=['POST'])
def delete_seed():
    doc_id = request.form['doc_id']

    elastic.delete_seed(doc_id)

    return "delete successfully"


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


@app.template_filter("titlecase")
def filter_titlecase(sentence):
    """A titlecase filter for the jinja2 templates.

    The standard "title" doesn't quite cut it.

    Args:
        sentence (str): the word or words that should be titlecased.
    """
    def _titlecase(word):
        if word in special:
            return word
        else:
            return word.title()

    special = ["the", "of", "in", "on", "at", "from"]

    return " ".join(map(_titlecase, sentence.split()))


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
    return some_date.strftime("%Y-%m-%d")


@app.template_filter("engldate")
def filter_engldate(some_date):
    """Returns the english date format of a given date.

    Args:
        some_date (datetime.date): the given date object.

    Returns:
        str: the english date (DD/MM/YYYY)
    """
    return some_date.strftime("%d/%m/%Y")


@app.template_filter("isomonth")
def filter_isomonth(some_date):
    """Returns the ISO month format of a given date.

    Args:
        some_date (datetime.date): the given date object.

    Returns:
        str: the ISO month (YYYY-MM)
    """
    return some_date.strftime("%Y-%m")


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

    print(baskets)
    for basket, mapped in zip(baskets, mapping):
        if obj["number"] < basket:
            return mapped
    # this case should normally not match, but just in case...
    return mapping[-1]


if __name__ == "__main__":
    # app = create_app(config.DATABASE_URI, debug=True)
    app.debug = True
    app.run()
