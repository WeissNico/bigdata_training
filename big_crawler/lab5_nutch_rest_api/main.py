import traceback
import hashlib
import time
import logging
import datetime as dt

from pymongo import MongoClient

from elastic import Elastic
from plugin_eurlex import EurlexPlugin
from py_crawl_api import crawlerSites

# setup the logger:
logging.basicConfig(format="[%(asctime)s] %(levelname)s: %(message)s",
                    level=logging.DEBUG)

# connect to the mongoDB
client = MongoClient("mongodb://159.122.175.139:30017")
db = client["crawler"]

elasticDB = Elastic()

collection = db.eurlex_webpage
# clear collection
collection.delete_many({})

# get new Documents from the eurlex-site
el_plugin = EurlexPlugin(db.eurlex_plugin)
# el_plugin.retrieve_new_documents()
# el_plugin.enrich_documents()

seed_list = []
today = dt.datetime.combine(dt.date.today(), dt.time.min)
for doc in db.eurlex_plugin.find({"crawl_date": {"$eq": today}}):
    seed_list.append(doc["url"])

# add manually generated seeds.
with open("big_crawler/lab5_nutch_rest_api/demo_seeds.txt", "r") as fl:
    for line in fl:
        seed_list.append(line[:-1])

# crawl new sites
status = crawlerSites(seedList=seed_list, collectionId="eurlex", counter=1)
if status != 1:
    raise RuntimeError

# insert new crawled sites into elastic
cursor = collection.find({})
for document in cursor:
    metadata = {}

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

    metadata_finder = db.eurlex_plugin.find({"url": doc_url})
    source_meta = {}
    if metadata_finder.count() > 0:
        source_meta = {k: v for k, v in metadata_finder[0].items()
                       if k[:1] != "_"}

    if not elasticDB.exist_document(doc_url, doc_hash):
        doc = {
            # "inlinks": document.get("inlinks", ""),
            # "outlinks": document.get("outlinks", ""),
            "baseUrl": doc_url,
            "contentType": document.get("contentType", ""),
            "title": document.get("title", ""),
            "text": document.get("text", ""),
            "tags": [],
            "document_metadata": metadata,
            "source_metadata": source_meta,
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
