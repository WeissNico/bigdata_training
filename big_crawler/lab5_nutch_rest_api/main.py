from pymongo import MongoClient
import traceback
import hashlib
import time
import logging

from elastic import Elastic
from plugin_eurlex import get_new_documents
from py_crawl_api import crawlerSites
client = MongoClient("mongodb://159.122.175.139:30017")
db = client["crawler"]

elasticDB = Elastic()

collection = db.test_webpage
# clear collection
collection.remove({})

# crawl documents
# seed_list = [
# ("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32013L0036"
#  "&from=EN"),
# ("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014L0065"
#  "&from=DE"),
# ("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0600"
#  "&from=DE"),
# ("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014R0596"
#  "&from=DE"),
# ("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32014L0057"
#  "&from=DE"),
# ("https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32015L2366"
#  "&from=EN")]

# get new Documents from the eurlex-site
documents = get_new_documents()
seed_list = []
for doc in documents:
    seed_list.append(doc["link"])

# crawl new sites
status = crawlerSites(seedList=seed_list, collectionId="test", counter=2)
if status != 1:
    raise RuntimeError

# insert new crawled sites into elastic
cursor = collection.find({})
for document in cursor:
    try:
        metadata = ""

        if document.get("metadata") is not None:
            try:
                metadata = {
                  (key if isinstance(key, str) else key.decode("utf-16")):
                  (val if isinstance(val, str) else val.decode("CP1252"))
                  for key, val in document["metadata"].items()
                }
            except Exception as e:
                try:
                    #
                    metadata = {
                      (key if isinstance(key, str) else key.decode("utf-8")):
                      (val if isinstance(val, str) else val.decode("utf-16"))
                      for key, val in document["metadata"].items()
                    }
                except Exception as e:
                    print(traceback.format_exc())

        # if the site was not properly parsed it is ignored
        if not document.get("content"):
            logging.info(f"Ignored page '{document.get('url')}' due to missing"
                         " content!")
            continue
        hash_object = hashlib.sha256(document.get("content"))
        doc_hash = hash_object.hexdigest()
        doc_url = document.get("baseUrl")

        if elasticDB.exist_document(doc_url, doc_hash):
            doc = {
                # "inlinks": document.get("inlinks", ""),
                # "outlinks": document.get("outlinks", ""),
                "baseUrl": doc_url,
                "contentType": document.get("contentType", ""),
                "title": document.get("title", ""),
                "text": document.get("text", ""),
                "tags": [],
                "document_metadata": metadata,
                "source_metadata": metadata,
                "hash": doc_hash,
                "version": time.time()
            }

            # document id
            doc_id = f"{doc_hash}#{time.time()}"
            # push into elastic,... the id is the hash + a timestamp
            elasticDB.insert_document(doc=doc, doc_id=doc_id)

        # if document.get("inlinks") is not None:
        #    binary = document["content"]

        #    with open(os.path.expanduser("~/Desktop/data/nutch/" +
        #                                 doc_id.replace("/","#")
        #                                 .replace(":", ";")), "wb") as fout:
        #        # fout.write(base64.decodebytes(binary))
        #        fout.write(binary)
        #        print(doc_id.replace("/","#"))

    except Exception as e:
        print(document["_id"])
        print(traceback.format_exc())
