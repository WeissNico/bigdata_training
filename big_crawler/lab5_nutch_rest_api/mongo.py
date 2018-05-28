from pymongo import MongoClient
from elastic import Elastic
import json
import os
import base64
import traceback
client = MongoClient('mongodb://159.122.175.139:30017')
db = client['crawler']

elastic = Elastic()

collection = db.webpage


cursor = collection.find({})
for document in cursor:
    try:
        metadata = ""

        if document.get('metadata') != None:
            try:
                metadata = {
                (key if isinstance(key, str) else key.decode('utf-16')): (val if isinstance(val, str) else val.decode('CP1252')) for
                key, val in document['metadata'].items()}
            except Exception as e:
                try:
                    metadata = {
                        (key if isinstance(key, str) else key.decode('utf-8')): (
                        val if isinstance(val, str) else val.decode('utf-16')) for
                        key, val in document['metadata'].items()}
                except Exception as e:
                    print(traceback.format_exc())

        doc = {
            'inlinks': document['inlinks'] if document.get('inlinks')!= None else "",
            'baseUrl': document['baseUrl'] if document.get('baseUrl')!= None else "",
            'contentType': document['contentType'] if document.get('contentType')!= None else "",
            'title': document['title'] if document.get('title')!= None else "",
            'text': document['text'] if document.get('text')!= None else "",
            'metadata': metadata,

        }
        doc_id = document['_id']
        elastic.insert_dokument(doc=doc, doc_id=doc_id)

        if document.get('inlinks')!= None:
            binary = document['content']

            with open(os.path.expanduser('~/Desktop/data/nutch/' + doc_id.replace('/','#').replace(':', ';')), 'wb') as file_out:
                # fout.write(base64.decodebytes(binary))
                file_out.write(binary)
                print(doc_id.replace('/','#'))

    except Exception as e:
        print(document['_id'])
        print(traceback.format_exc())


'''


file = collection.find_one({'_id': 'de.bayern.region-suedostoberbayern.www:http/verbandsarbeit/sitzungen/'})
binary = file['content']
name = file['_id'].replace('/', '#').replace(':', ';')

with open(os.path.expanduser('~/Desktop/data/nutch/'+name+'.html' ), 'wb') as file_out:
    # fout.write(base64.decodebytes(binary))
    file_out.write(binary)
    #print(doc_id.replace('/', '#'))
'''
'''

metadata =  { (key if isinstance(key,str) else key.decode('utf-8')) :(val if isinstance(val,str) else val.decode('cp1252')) for key, val in file['metadata'].items() }

doc = {
    'inlinks': file['inlinks'],
    'baseUrl': file['baseUrl'],
    'contentType': file['contentType'],
    'title': file['title'],
    'text': file['text'],
    'metdadata': metadata,

}
doc_id = file['_id']

elastic = Elastic()
elastic.insert_dokument(doc=doc, doc_id=doc_id)

'''
