from elasticsearch import Elasticsearch, RequestsHttpConnection
es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
from flask import Flask, request, render_template
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
    results = es.search(index="testcase", body={"query": {"simple_query_string": {"query":search_text}}, "highlight": {"fields": {"*" : {"pre_tags" : ["<b>"], "post_tags" : ["</b>"]}}}})
    data = [doc for doc in results['hits']['hits']]
    #print("search for %s returned %s hits" % (search_text,len(data)))
    formated_list = ""
    search_result = list()
    for doc in data:
        filename = doc['_id']
        date = doc['_source']['metadata']['date']
        text = doc['highlight']['text'][:200] if doc.get('highlight', {}).get('text')!= None else ""
        tags = doc['_source']['contentType']
        print("%s) %s" % (filename,tags ))
        #formated_list += '<tr><td style="width: 40px">%s</td><td style="width: 10%%"> %s</td><td> %s</td><td> %s</td></tr>' \
        #                 % (Filename,Date, Text,Tags)
        search_result.append({'filename':filename, 'date':date, 'text':text, 'tags':tags})

    #table_header = '<tr><th  style="width: 10%">Filename<th/><th  style="width: 10%;">Date <th/><th  style="width: 60%;">Text <th/><th style="width: 20%;">Tags <th/></tr>'
    #return basepage('<table>%s %s</table>' % (table_header,formated_list))
    return render_template('search.html', results=search_result)

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

if __name__ == "__main__":
    #app = create_app(config.DATABASE_URI, debug=True)
    app.debug = True
    app.run()

