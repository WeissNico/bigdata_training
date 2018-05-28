from pymongo import MongoClient
import json
import os
import base64
import traceback
#%%
from elastic import Elastic
#%%
import pickle
filename = 'text_model.sav'
# load the model from disk
classify2 = pickle.load(open(filename, 'rb'))
#%%
z = classify2.predict(['''eiterte Fassung) vor. Diese Online-Fassung enthält  neben dem Anhang als Teil 
                des  Bayer-Konzernabschlusses  weiterführende Informatio-nen  zum Lagebericht.
                Den „Geschäftsbericht 2017 – Erweiterte  Fassung“ finden Sie unter www.bayer.de/GB17
 A Zusammengefasster Lagebericht
 Bayer-Geschäftsbericht 2017 1EBITDAvor Sondereinflüssen KonzernergebnisUmsatzLieferantenmanagement
 Investitionen in Forschung und EntwicklungBereinigtesErgeb'''])
print(z)
# %%
  
import pdfminer.high_level
import io

def get_text_from_pdf_2(text):
    outp = io.StringIO()
    with io.StringIO(text) as fp:
        pdfminer.high_level.extract_text_to_fp(fp,outp, output_type='text')
    text = outp.getvalue()
    outp.close()
    return text
# %%

client = MongoClient('mongodb://159.122.175.139:30017')
db = client['crawler']

collection = db.webpage
#%%
elastic = Elastic()

#%%
cursor = collection.find({})
for document in cursor:
    try:
        metadata = ""

        if document.get('metadata') != None:
            try:
                metadata = {
                (key if isinstance(key, str) else key.decode('utf-8')): (val if isinstance(val, str) else val.decode('CP1252')) for
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
            'outlinks': document['outlinks'] if document.get('outlinks') != None else "",
            'baseUrl': document['baseUrl'] if document.get('baseUrl')!= None else "",
            'contentType': document['contentType'] if document.get('contentType')!= None else "",
            'title': document['title'] if document.get('title')!= None else "",
            'text': document['text'] if document.get('text')!= None else "",
            'metdadata': metadata,

        }
        
        #if doc['contentType']=='text/pdf':
        #    text = get_text_from_pdf_2(document['content'])
        #else:
        #    text =  doc['text']

        text = doc['text']

        z = classify2.predict([text])
        print("%s - %s " % (doc['title'],z[0]))
        
        if z[0]!="ignore":
            
            doc_id = document['_id']
            elastic.insert_dokument(doc=doc, doc_id=doc_id)

    except Exception as e:
        print(document['_id'])
        print(traceback.format_exc())

#%%
import sys
sys.exit(0)

#%%

file = collection.find_one({'_id': 'de.bayern.region-suedostoberbayern.www:http/verbandsarbeit/sitzungen/'})
binary = file['content']
name = file['_id'].replace('/', '#').replace(':', ';')
  

#%%
with open(os.path.expanduser('~/Desktop/data/nutch/'+name+'.html' ), 'wb') as file_out:
    # fout.write(base64.decodebytes(binary))
    file_out.write(binary)
    #print(doc_id.replace('/', '#'))
#%%

metadata =  { (key if isinstance(key,str) else key.decode('utf-8')) :(val if isinstance(val,str) else val.decode('cp1252')) for key, val in file['metadata'].items() }

doc = {
    'inlinks': document['inlinks'] if document.get('inlinks') != None else "",
    'outlinks': document['outlinks'] if document.get('outlinks') != None else "",
    'baseUrl': document['baseUrl'] if document.get('baseUrl') != None else "",
    'contentType': document['contentType'] if document.get('contentType') != None else "",
    'title': document['title'] if document.get('title') != None else "",
    'text': document['text'] if document.get('text') != None else "",
    'metdadata': metadata,

}
doc_id = file['_id']
#%%
elastic = Elastic()
elastic.insert_dokument(doc=doc, doc_id=doc_id)
