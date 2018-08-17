from pymongo import MongoClient
import traceback
import hashlib
import time

from lab5_nutch_rest_api.elastic import Elastic
from lab5_nutch_rest_api.plugin_eurlex import get_new_documents
from lab5_nutch_rest_api.py_crawl_api import crawlerSites
client = MongoClient('mongodb://159.122.175.139:30017')
db = client['crawler']

elastic = Elastic()

collection = db.test_webpage
#clear collection
collection.remove({})

# crawl documents
#seed_list = [
#"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32013L0036&from=EN",
#"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014L0065&from=DE",
#"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0600&from=DE",
#"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0596&from=DE",
#"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014L0057&from=DE",
#"https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32015L2366&from=EN"]

documents = get_new_documents() #get new Documents from the eurlex-site
seed_list = []
for doc in documents:
    seed_list.append(doc['link'])

status = crawlerSites(seedList= seed_list, collectionId="test", counter=2)  #crawle site new sites
if status != 1:
    raise RuntimeError
#load data to elastic

cursor = collection.find({})
for document in cursor: #insert new crawled sites into elastic
    try:
        metadata = ""

        if document.get('metadata') != None:
            try:
                metadata = {
                (key if isinstance(key, str) else key.decode('utf-16')): (val if isinstance(val, str) else val.decode('CP1252')) for
                key, val in document['metadata'].items()}
            except Exception as e:
                try:
                    #
                    metadata = {
                        (key if isinstance(key, str) else key.decode('utf-8')): (
                        val if isinstance(val, str) else val.decode('utf-16')) for
                        key, val in document['metadata'].items()}
                except Exception as e:
                    print(traceback.format_exc())

        if not document.get('content'):  #if the site was not properly parsed it get ignored
            print('not')
            continue
        hash_object = hashlib.sha256(document.get('content'))
        hash = hash_object.hexdigest()
        baseUrl = document.get('baseUrl')

        new_or_modified = elastic.exist_document(baseUrl, hash)
        if new_or_modified == 0:
        #print(hash)
            doc = {
                #'inlinks': document['inlinks'] if document.get('inlinks')!= None else "",
                #'outlinks': document['outlinks'] if document.get('outlinks') != None else "",
                'baseUrl': baseUrl,
                'contentType': document['contentType'] if document.get('contentType')!= None else "",
                'title': document['title'] if document.get('title')!= None else "",
                'text': document['text'] if document.get('text')!= None else "",
                'tags': [],
                'metadata': metadata,
                'hash': hash,
                'version': time.time()
            }

            doc_id = hash+'#'+str(time.time())#document['_id']
            elastic.insert_dokument(doc=doc, doc_id=doc_id)   #push into elastic,... the id is the hash + a timestamp

        #if document.get('inlinks')!= None:
        #    binary = document['content']

        #    with open(os.path.expanduser('~/Desktop/data/nutch/' + doc_id.replace('/','#').replace(':', ';')), 'wb') as file_out:
        #        # fout.write(base64.decodebytes(binary))
        #        file_out.write(binary)
        #        print(doc_id.replace('/','#'))

    except Exception as e:
        print(document['_id'])
        print(traceback.format_exc())

