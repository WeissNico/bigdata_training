"""This module aims to provide some simple mock functions for creating
some objects too feed our frontend with.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import random
import os
from datetime import timedelta

import bson.objectid
import bson.errors

import utility as ut


DIR = os.path.dirname(__file__)


TYPES = ["Regulation", "Guideline", "Directive", "FAQ", "Article"]
IMPACTS = ["high", "medium", "low"]
CATEGORIES = ["Securities", "Risk management", "General", "GDPR"]
SOURCES = ["Inhouse",
           "https://eur-lex.europa.eu/legal-content/de/txt/",
           "https://voeb.de/download/",
           ("https://bafin.de/DE/PublikationenDaten/Jahresbericht/"
            "Jahresbericht/2016/Kapitel2/"),
           "https://bafin.de/sharedDocs/Veroeffentlichungen/DE",
           "https://bis.org/veroeffentlichungen/download/"]
DOCUMENTS = ["Anwendung der Richtlinie 2007/64/EG im operativen Geschäft",
             ("Änderungen im Verfahren durch Inkraftsetzung der Richtlinie "
              "(EU) 2015/2366"),
             ("RICHTLINIE (EU) 2015/2366 DES EUROPÄISCHEN PARLAMENTS UND DES "
              "RATES vom 25. November 2015 über Zahlungsdienste im Binnenmarkt"
              ", zur Änderung der Richtlinien 2002/65/EG, 2009/110/EG und "
              "2013/36/EU und der Verordnung (EU) Nr. 1093/2010 sowie zur "
              "Aufhebung der Richtlinie 2007/64/EG"),
             ("RICHTLINIE 2007/64/EG DES EUROPÄISCHEN PARLAMENTS UND DES RATES"
              " vom 13. November 2007 über Zahlungsdienste im Binnenmarkt, zur"
              " Änderung der Richtlinien 97/7/EG, 2002/65/EG, 2005/60/EG und "
              " 2006/48/EG sowie zur Aufhebung der Richtlinie 97/5/EG"),
             ("Entwurf Mindestanforderungen an die Sicherheit von "
              "Internetzahlungen, Konsultation 02/2015"),
             ("Fragen und Antworten zu den Mindestanforderungen an die "
              "Sicherheit von Internetzahlungen (MaSI)"),
             ("VERORDNUNG (EU) Nr. 575/2013 DES EUROPÄISCHEN PARLAMENTS UND "
              "DES RATES vom 26. Juni 2013 über Aufsichtsanforderungen an "
              "Kreditinstitute und Wertpapierfirmen und zur Änderung der "
              "Verordnung (EU) Nr. 646/2012"),
             ("Principles for effective risk data aggregation and risk "
              "reporting")]
KEYWORDS = ["management", "aggregation", "principle", "bank", "Verordnung",
            "Richtlinie", "Kredite", "Risko", "risk", "Zahlungsdienstleister",
            "Mitgliedsstaaten", "Europäische Union", "european", "Zahler",
            "Zahlungsdienstnutzer", "Artikel", "Kommission", "Verordnung",
            "Vorhaben", "Wertpapierrecht", "Kapitalmarkt",
            "Richtlinienvorschlag", "Bankaufsichtsrecht", "Aufsichtsrat",
            "Aufsichtsbehörden", "credits", "securities", "national",
            "international"]
ENTITIES = ["Deutsche Bank", "BAFIN", "HSBC Bank", "Europäische Union", "EU",
            "Deutsche Bundesbank", "EZB"]
STATUS = ["open", "waiting", "finished"]


def _random_frequencies(pool, min_reps=50, max_reps=100):
    """Create a dict with random normalized frequencies."""
    words = []
    for i in range(random.randrange(min_reps, max_reps)):
        words.append(random.choice(pool))
    freqs = ut.frequencies(words)
    minimum = min(freqs.values())
    maximum = max(freqs.values())
    if maximum-minimum == 0:
        freqs = {w: 1 for w, v in freqs.items()}
        return freqs
    freqs = {w: (v - minimum) / (maximum - minimum)
             for w, v in freqs.items()}
    return freqs


class Mocker():
    def __init__(self, mongo_collection, renew=False):
        """Creates a new mock module and connects to a mongo_db collection.

        If renew is given drops the collection first.

        Args:
            mongo_collection (pymongo.collection.Collection): a collection.
            renew (bool): whether all entries should be dropped.

        Return:
            Mocker: a new mock client.
        """
        self.coll = mongo_collection

        if renew:
            self.coll.delete_many({})

    def set_seed(self, cur_date):
        """Helper function to set the seed to a date, for consistency."""
        random.seed(cur_date)

    def get_documents(self, cur_date):
        """Returns all mockuments for the given date.

        Args:
            cur_date (datetime.date): the current date

        Returns:
            list: a list of documents for the given date
        """
        docs = self.coll.find({"date": cur_date})
        return docs

    def get_document(self, doc_id):
        """Returns a mockument with a given id.

        Args:
            doc_id (str): the documents id.

        Returns:
            dict: a saved document, if existant.
        """
        try:
            obj_id = bson.objectid.ObjectId(doc_id)
        except bson.errors.InvalidId:
            return None
        doc = self.coll.find_one({"_id": obj_id})
        return doc

    def set_document(self, doc, doc_id=None):
        """Sets a mockument to a given id.

        Args:
            doc_id (str): the documents id. Defaults to None, which just
                inserts a new document
            doc (dict): the new document.

        Returns:
            bson.objectid.ObjectId: the id of the inserted or updated document.
                or None.
        """
        obj_id = None
        try:
            obj_id = bson.objectid.ObjectId(doc_id)
        except bson.errors.InvalidId:
            obj_id = bson.objectid.ObjectId()

        result = self.coll.update_one({"_id": obj_id}, {"$set": doc},
                                      upsert=True)
        if result.modified_count > 0 or result.upserted_id is not None:
            return obj_id
        return None

    def create_random_date(self, max_date=None, min_date=None):
        """Creates a random date using the provided constraints.

        Args:
            min_date (datetime.date): the minimum age this date should become.
                Defaults to None, which equals one year before max_date.
            max_date (datetime.date): the maximum date this date should become.
                Defaults to None, which equals today.

        Returns:
            datetime.date: a new random date.
        """
        YEAR = timedelta(days=365)

        if max_date is None:
            max_date = ut.from_date()
        if min_date is None:
            min_date = max_date - YEAR

        delta = max_date - min_date
        days = random.randint(0, delta.days)
        return ut.from_date(min_date + timedelta(days=days))

    def get_calendar(self, cur_date):
        """Returns the calendar for the given date in a efficient way.

        Args:
            cur_date (datetime.datetime): the date the current dashboard is
                displayed for.

        Returns:
            list: a list of date-dicts.
        """
        year_range = ut.get_year_range(cur_date)
        docs = self.coll.aggregate([
            {
                "$match": {
                    "date": {
                        "$gt": year_range[0],
                        "$lte": year_range[1]
                    }
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "n_open": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "open"]}, 1, 0]
                        }
                    },
                    "n_waiting": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "waiting"]}, 1, 0]
                        }
                    },
                    "n_finished": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "finished"]}, 1, 0]
                        }
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id",
                    "n_open": 1,
                    "n_waiting": 1,
                    "n_finished": 1
                }
            },
            {
                "$sort": {"date": -1}
            }
        ])
        return docs

    def get_date(self, cur_date):
        """Returns the aggregate of jobs from the database.

        Args:
            cur_date (datetime.datetime): the date the aggregate should be
                calculated for.

        Returns:
            list: a list of date-dicts.
        """
        docs = self.coll.aggregate([
            {
                "$match": {
                    "date": cur_date
                }
            },
            {
                "$group": {
                    "_id": "$date",
                    "n_open": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "open"]}, 1, 0]
                        }
                    },
                    "n_waiting": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "waiting"]}, 1, 0]
                        }
                    },
                    "n_finished": {
                        "$sum": {
                            "$cond": [{"$eq": ["$status", "finished"]}, 1, 0]
                        }
                    }
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "date": "$_id",
                    "n_open": 1,
                    "n_waiting": 1,
                    "n_finished": 1
                }
            },
            {
                "$limit": 1
            }
        ])
        return next(docs, None)

    def create_mock_date(self, cur_date, **kwargs):
        """Creates a mocked date object.

        Args:
            cur_date (datetime.datetime): the date this mock date is for
            **kwargs (dict): other keys, that should be updated in the final
                obj.

        Returns:
            dict: some mock date object.
        """
        mock_date = {
            "date": cur_date
        }
        if cur_date < ut.from_date():
            mock_date[f"n_finished"] = random.randint(0, 6)
            mock_date[f"n_waiting"] = 0
            mock_date[f"n_open"] = 0
        else:
            for st in ["open", "waiting", "finished"]:
                mock_date[f"n_{st}"] = random.randint(0, 4)

        mock_date.update(kwargs)
        return mock_date

    def get_or_create_date(self, cur_date):
        """Retrieves a document or creates a new mocked one.

        Args:
            cur_date (datetime.datetime): the date this mock date is for

        Returns:
            dict: some date object.
        """
        date_obj = self.get_date(cur_date)
        if date_obj is None:
            date_obj = self.create_mock_date(cur_date)
        return date_obj

    def get_or_create_calendar(self, cur_date):
        """Returns a made up (and real) calendar for the given date.

        Args:
            cur_date (datetime.datetime): the date this calendar is built
                around.

        Returns:
            tuple: first entry is a list of calendar dates,
                second entry is a dict for the current_date.
        """
        # merge the two calendars but prioritize the real one
        calendar = self.get_calendar(cur_date)
        mock_calendar = ut.generate_date_range(cur_date)

        cur_real = next(calendar, None)

        cal = []
        for cur_mock in mock_calendar:
            if cur_real is not None and cur_real["date"] == cur_mock:
                cal.append(cur_real)
                cur_real = next(calendar, None)
            else:
                cal.append(self.create_mock_date(cur_mock))
        return cal

    def create_mockument(self, cur_date, **kwargs):
        """Creates a mocked document, binding the given kw-args if necessary.

        Args:
            cur_date (datetime.date): the date this document should be created
                for
            **kwargs (dict): other keys, that should be updated in the final
                obj.

        Returns:
            dict: some mock document.
        """
        doc = {}

        doc["date"] = cur_date
        doc["new"] = random.random() < 0.7
        doc["type"] = random.choice(TYPES)
        doc["impact"] = random.choice(IMPACTS)
        doc["category"] = random.choice(CATEGORIES)
        doc["source"] = random.choice(SOURCES)
        doc["document"] = random.choice(DOCUMENTS)
        # create some quantity
        num_words = random.randint(102, 279877)
        num_lines = num_words // random.randint(11, 19)
        doc["quantity"] = {"lines": num_lines, "words": num_words}
        # create some change
        num_lines_rem = 0
        num_lines_add = num_lines
        if not doc["new"]:
            num_lines_rem = random.randint(0, num_lines)
            num_lines_add = random.randint(0, num_lines)
        doc["change"] = {"lines_added": num_lines_add,
                         "lines_removed": num_lines_rem}
        doc["status"] = random.choice(STATUS)
        # if this mock document is older than today's date, mark it assigned
        if cur_date < ut.from_date():
            doc["status"] = "finished"

        # make up some frequent words for the word cloud

        doc["keywords"] = _random_frequencies(KEYWORDS,
                                              min_reps=10, max_reps=30)
        doc["entities"] = _random_frequencies(ENTITIES,
                                              min_reps=3, max_reps=10)

        # put in the remaining kwargs
        doc.update(kwargs)
        doc_id = self.set_document(doc)
        return self.get_document(doc_id)

    def get_or_create_documents(self, cur_date, num):
        """Returns all mockuments for the given date.

        If the desired number is not met, creates new documents.

        Args:
            cur_date (datetime.date): the current date
            num (int): the desired number of documents, defaults to None.
                (no change if there are any documents, otherwise random 3-10).

        Returns:
            list: a list of documents for the given date
        """
        docs = self.get_documents(cur_date)

        if num is None:
            if docs.count() > 0:
                return docs
            else:
                num = random.randint(3, 10)
        diff = num - docs.count()
        if diff > 0:
            for i in range(diff):
                self.create_mockument(cur_date)
        return self.get_documents(cur_date)

    def create_connected_documents(self, doc_id, num=None):
        """Creates a random number of connected documents, using other docs.

        Args:
            doc_id (str): the current documents id.
            num (int): the number of random documents.
                Defaults to None, which means 1-10 documents.

        Returns:
            list: a list of connected documents.
        """
        if num is None:
            num = random.randint(1, 10)
        documents = []
        for i in range(1, num):
            new_doc = self.create_mockument(self.create_random_date())
            similarity = random.random() * 0.7 + 0.3
            new_doc["connections"] = {
                doc_id: {
                    "doc_id": doc_id,
                    "similarity": similarity
                }
            }
            self.set_document(new_doc, new_doc["_id"])
            documents.append(new_doc)
        return documents

    def get_or_create_connected(self, doc_id):
        """Returns all connected documents or creates some mocked ones.

        Args:
            doc_id (str): the document whose connections should be found.

        Returns:
            list: a list of connected documents.
        """
        conn = self.coll.find({f"connections.{doc_id}": {"$exists": True}})
        if conn.count() == 0:
            return self.create_connected_documents(doc_id)
        return conn

    def add_text_to_doc(self, doc_id, fname, force=False):
        """Adds a text to a given document and saves it in the memory-db.

        Args:
            doc_id (str): the document, to which the text should be added.
            fname (str): the name of the file containing the text.
            force (bool): whether the text should be overwritten or not.

        Returns:
            dict: the updated document.
        """
        path = os.path.join(DIR, fname)

        content = None
        with open(path, "r") as fl:
            content = fl.read()
        doc = self.get_document(doc_id)
        if force or "text" not in doc:
            doc["text"] = content
        self.set_document(doc, doc_id)
        return doc

    def create_versions(self, doc_id, num=None):
        """Creates a random number of previous document versions.

        Args:
            doc_id (str): the document, for which the previous versions should
                be created.
            num (int): the number of random documents.
                Defaults to None, which means 1-3 documents.

        Returns:
            list: a list of documents which share the same title, source and
                type
        """
        doc = self.get_document(doc_id)

        # if the document has a version_key no further versions are created!
        if "version_key" in doc:
            return []
        # for simplicity reasons, a document which is marked as new can not
        # have any ancestors
        if doc["new"]:
            return []

        end = doc["date"]
        start = None

        if num is None:
            num = random.randint(1, 3)

        documents = []
        for i in range(num):
            new_doc = self.create_mockument(self.create_random_date(
                                                max_date=end,
                                                min_date=start),
                                            version_key=doc["_id"],
                                            document=doc["document"],
                                            type=doc["type"],
                                            source=doc["source"],
                                            new=False)
            documents.append(self.add_text_to_doc(new_doc["_id"],
                             os.path.join(DIR, "dummy_text_mod.txt")))
        # not completely correct, since all docs are marked as modified...
        return documents

    def get_versions(self, doc_id):
        """Returns all documents that have the same title, source and type.

        Args:
            doc_id (str): the id of the document, whose versions should be
                found.

        Returns:
            list: a list of documents, which are versions of each other.
        """
        cur_doc = self.get_document(doc_id)
        vk = cur_doc["_id"]
        if "version_key" in cur_doc:
            vk = cur_doc["version_key"]
        docs = self.coll.find({"$or": [{"version_key": vk},
                                       {"_id": vk}],
                               "_id": {"$ne": cur_doc["_id"]}})
        return docs

    def get_or_create_versions(self, doc_id):
        """Returns all documents, that have the same title, source and type.

        If they don't exist, creates a random amount of versions.

        Args:
            doc_id (str): the id of the document, whose versions should be
                found.

        Returns:
            list: a list of documents, which are versions of each other.
        """
        self.add_text_to_doc(doc_id, os.path.join(DIR, "dummy_text.txt"))

        docs = self.get_versions(doc_id)
        docs = [self.add_text_to_doc(d["_id"],
                                     os.path.join(DIR, "dummy_text_mod.txt"))
                for d in docs]

        if not docs:
            docs = self.create_versions(doc_id)
        return docs
