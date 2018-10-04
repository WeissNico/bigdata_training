import traceback
import hashlib
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
logging.debug(client.server_info())
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
el_plugin = EurlexPlugin(db.eurlex_plugin,
                         mongo_version=client.server_info()["versionArray"])
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
status = crawlerSites(seedList=seed_list, collectionId="eurlex", counter=5)
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

    num_sources = db.eurlex_plugin.count_documents({"url": doc_url})
    sources = db.eurlex_plugin.find({"url": doc_url})
    source_meta = {}
    # if there are results for the source
    for source in sources:
        # flatten the source meta
        cur_meta = dict(source.get("metadata", {}),
                        title=source.get("title", "no title"),
                        date=source.get("date"),
                        crawl_date=source.get("crawl_date"),
                        url=doc_url)
        source_meta.update(cur_meta)

    # concatenate the metadata
    metadata.update(source_meta)

    # prepare a nearly naked document:
    doc = {
        "content": document.get("content"),
        "text": document.get("text", ""),
        "metadata": metadata
    }

    if not elasticDB.exist_document(doc_url, doc_hash):
        logging.debug(f"Insert document {doc_url} into the elasticsearch DB.")
        # push into elastic,... the id will be created automatically
        elasticDB.insert_document(doc)

    # if document.get("inlinks") is not None:
    #    binary = document["content"]

    #    with open(os.path.expanduser("~/Desktop/data/nutch/" +
    #                                 doc_id.replace("/","#")
    #                                 .replace(":", ";")), "wb") as fout:
    #        # fout.write(base64.decodebytes(binary))
    #        fout.write(binary)
    #        print(doc_id.replace("/","#"))
