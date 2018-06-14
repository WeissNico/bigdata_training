from elasticsearch import Elasticsearch, RequestsHttpConnection
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
from flask import Flask, request, render_template
from settings import ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORT, ELASTICSEARCH_HOST, ELASTICSEARCH_PORT
from elastic import Elastic
from google import google

app = Flask(__name__)

elastic = Elastic()
@app.route("/search", methods=['GET', 'POST'])
def search():
    search_text = request.args.get('search')
    auth = (ELASTICSEARCH_USER,ELASTICSEARCH_PASSWORT)
    es = Elasticsearch(host=ELASTICSEARCH_HOST,
                       port=ELASTICSEARCH_PORT,
                       connection_class=RequestsHttpConnection,
                       use_ssl = True,
                       timeout=220,
                       max_retries=10, retry_on_timeout=True,
                       http_auth=auth)
    #res = requests.get(ELASTIC_URL+"/=")
    results = es.search(index="testcase", body={"query": {"simple_query_string": {"query":search_text}}, "highlight": {"fields": {"*" : {"pre_tags" : ["<b>"], "post_tags" : ["</b>"]}}}})
    data = [doc for doc in results['hits']['hits']]

    search_result = list()
    for doc in data:
        if doc.get('highlight', {}).get('text') != None or doc.get('highlight', {}).get('tags') != None:
            link = doc['_source']['baseUrl']
            id = doc['_id']
            filename = doc['_source']['title'] if doc.get('_source', {}).get('title') != "" else "no title"
            date = doc['_source']['metadata']['date'] if doc.get('_source', {}).get('metadata').get('date') != None else 'no date'
            text = doc['highlight']['text'][:200] if doc.get('highlight', {}).get('text') != None else doc['_source']['text'][:200],
            tags = list(doc['_source']['tags']) if doc.get('_source', {}).get('tags') != None else [],
            print("%s) %s" % (filename, tags))

            search_result.append({'id':id, 'filename':filename, 'date':date, 'text':text, 'tags':tags, 'link': link})

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
    return render_template('seeds.html', seeds = res)

@app.route("/train")
def train():
    doc_id = request.args.get('doc_id')
    if doc_id == None:
        return render_template('warning.html', warning="DocId is missing")
    else:
        url = '<iframe src="https://www.w3schools.com"></iframe>'
        return render_template('train.html', tags = ["Tag1","Tag2","Tag4"], url = url  )

@app.route("/download") #without endpoint an an AssertionError occurs
def download():
    doc_id = request.args.get('doc_id')
    if doc_id == None:
        return render_template('warning.html', warning="DocId is missing")
    else:
        return "Download should happen here"


@app.route("/")
def home():
    return render_template('home.html', news="No news")


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
        "name" :name,
        "category": category,
        "doc_id":doc_id
    }

    elastic.set_seed(seed)

    return "update successfully"

@app.route("/deleteSeed", methods=['POST'])
def delete_seed():
    doc_id = request.form['doc_id']

    elastic.delete_seed(doc_id)

    return "delete successfully"

if __name__ == "__main__":
    #app = create_app(config.DATABASE_URI, debug=True)
    app.debug = True
    app.run()

