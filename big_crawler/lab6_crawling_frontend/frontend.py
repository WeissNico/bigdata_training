from elasticsearch import Elasticsearch, RequestsHttpConnection
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
from flask import Flask, request
from basepage import basepage
from settings import ELASTICSEARCH_USER, ELASTICSEARCH_PASSWORT, ELASTICSEARCH_HOST, ELASTICSEARCH_PORT
app = Flask(__name__)

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
    results = es.search(index="imission", body={"query": {"simple_query_string": {"query":search_text}}})
    data = [doc for doc in results['hits']['hits']]
    print("search for %s returned %s hits" % (search_text,len(data)))
    formated_list = ""
    for doc in data:
        Filename = doc['_id']
        Date = doc['_id']
        Text = doc['_source']['text']
        Tags = doc['_source']['text']
        print("%s) %s" % (Filename,Tags ))
        formated_list += '<tr><td>%s</td><td> %s</td><td> %s</td><td> %s</td></tr>' % (Filename,Date, Text,Tags)

    table_header = '<th style="width: 30%;"><td>Filename<td/><td>Date <td/><td>Text <td/><td>Tags <td/></th>'
    return basepage("<table>%s %s</table>" % (table_header,formated_list))

@app.route("/")
def home():
    return basepage("""<div class="starter-template">
        <h1>Search for Wacker</h1>
        <p class="lead">Search easy and fast.<br> All you get is this text.  </div>""")

if __name__ == "__main__":
    #app = create_app(config.DATABASE_URI, debug=True)
    app.debug = True
    app.run()

