import traceback
import hashlib
import time
import logging
import datetime as dt
import base64

from pymongo import MongoClient

import utility as ut
from elastic import Elastic
from plugin_eurlex import EurlexPlugin
from py_crawl_api import crawlerSites

# setup the logger:
logging.basicConfig(format="[%(asctime)s] %(levelname)s: %(message)s",
                    level=logging.DEBUG)

# connect to the mongoDB
client = MongoClient("mongodb://159.122.175.139:30017")
db = client["crawler"]

elasticDB = Elastic(host=("portal-ssl223-11.bmix-lon-yp-2012af18-4749-4d32-"
                          "94a6-09573ff5ee35.3259324498.composedb.com"),
                    port=26611,
                    auth=("admin", "RYZUAYORFMEGJRCT"),
                    docs_index="eur_lex")

collection = db.eurlex_webpage
# clear collection
collection.delete_many({})

# get new Documents from the eurlex-site
el_plugin = EurlexPlugin(db.eurlex_plugin)
el_plugin.retrieve_new_documents()
el_plugin.enrich_documents()

seed_list = []
today = dt.datetime.combine(dt.date.today(), dt.time.min)
for doc in db.eurlex_plugin.find({"crawl_date": {"$eq": today}}):
    seed_list.append(doc["url"])

# add manually generated seeds.
with open("big_crawler/lab5_nutch_rest_api/demo_seeds.txt", "r") as fl:
    for line in fl:
        if line[:1] == "#":
            continue
        seed_list.append(line[:-1])

# crawl new sites
status = crawlerSites(seedList=seed_list, collectionId="eurlex", counter=1)
if status != 1:
    raise RuntimeError

# insert new crawled sites into elastic
cursor = collection.find({})
length = collection.count_documents({})
logging.debug(f"Adding {length} documents to the elasticsearch DB.")
for document in cursor:
    metadata = {}

    if document.get("metadata") is not None:
        # try to retrieve some metadata in different encodings.
        try:
            # try utf-16
            metadata = {
              (key if isinstance(key, str) else key.decode("utf-16")):
              (val if isinstance(val, str) else val.decode("CP1252"))
              for key, val in document["metadata"].items()
            }
        except Exception as e:
            try:
                # try utf-8
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

    num_metadata = db.eurlex_plugin.count_documents({"url": doc_url})
    metadata_finder = db.eurlex_plugin.find({"url": doc_url})
    source_meta = {}
    if num_metadata > 0:
        source_meta = {k: v for k, v in metadata_finder[0].items()
                       if k[:1] != "_"}

    # concatenate the metadatas
    metadata.update(source_meta)
    lines, words = ut.calculate_quantity(document.get("text", ""))

    if not elasticDB.exist_document(doc_url, doc_hash):
        doc = {
            # "inlinks": document.get("inlinks", ""),
            # "outlinks": document.get("outlinks", ""),
            "date": ut.from_date(metadata.get("date", None)),
            "source": doc_url,
            "hash": doc_hash,
            "version": time.time(),
            "content_type": document.get("contentType", ""),
            "content": base64.b64encode(document.get("content",
                                                     None)).decode(),
            "document": document.get("title", "No Title"),
            "text": document.get("text", ""),
            "tags": [],
            "keywords": {},
            "entities": {},
            "quantity": {"lines": lines, "words": words},
            "change": {"lines_added": lines, "lines_removed": 0},
            "metadata": metadata,
            "type": "?",
            "category": "?",
            "fingerprint": "placeholder",
            "version_key": 0,
            "connections": {},
            "impact": 0,
            "status": 0,
            "new": True,
        }

        # document id
        doc_id = f"{doc_hash}#{time.time()}"
        logging.debug(f"Insert document {doc_id} into the elasticsearch DB.")
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
