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
        text = utility.safe_dict_access(doc, ["highlight", "text"],
                                        None)
        hl_tags = utility.safe_dict_access(doc, ["highlight", "tags"],
                                           None)
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
    status_freqs = utility.frequencies(documents, lambda doc: doc["status"])
    current = mock.create_mock_date(db_date,
                                    n_open=status_freqs.get("open", 0),
                                    n_waiting=status_freqs.get("waiting", 0),
                                    n_finished=status_freqs.get("finished", 0))
    # create some mock calendar
    calendar = [mock.create_mock_date(d)
                for d in utility.generate_date_range(db_date)]

    # create sort order on the documents
    sort_by = request.args.get("sortby", "impact")
    desc = request.args.get("desc", "True").lower() == "true"

    documents = utility.sort_documents(documents, sort_key=sort_by, desc=desc)
    columns = ["type", "impact", "category", "source", "document", "change",
               "quantity", "status"]
    return render_template("dashboard.html",
                           calendar=calendar,
                           current=current,
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


if __name__ == "__main__":
    # app = create_app(config.DATABASE_URI, debug=True)
    app.debug = True
    app.run()
