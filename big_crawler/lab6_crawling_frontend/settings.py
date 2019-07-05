"""This little module contains all settings regarding our app."""

import logging
import os

ELASTICSEARCH_USER = os.environ.get("SHERLOCK_ES_USER", "admin")
ELASTICSEARCH_PASSWORD = os.environ.get("SHERLOCK_ES_PASSWORD",
                                        "RYZUAYORFMEGJRCT")
ELASTICSEARCH_HOST = os.environ.get(
    "SHERLOCK_ES_HOST",
    ("a68a95ee-0079-4637-9dab-e8048174f0d1.659dc287bad647f9b4"
     "fe17c4e4c38dcc.databases.appdomain.cloud"))
ELASTICSEARCH_PORT = os.environ.get("SHERLOCK_ES_PORT", 31791)
ELASTICSEARCH_CAFILE = os.environ.get(
    "SHERLOCK_ES_CAFILE",
    ("C:\\Users\\j.mueller\\.bluemix\\plugins\\cdb\\cdbcerts\\"
     "2e1c46d0-ce0b-11e8-b230-ced9d81cd3f4"))
ELASTICSEARCH_DOCS_INDEX = os.environ.get("SHERLOCK_ES_DOCS_INDEX", "sherlock")
LOGGING_LEVEL = logging.DEBUG

SECRET_KEY = os.environ.get("SHERLOCK_SECRET", "pl34se change th1s!")
"""The secret key for csrf-protection and so on. Please change."""

UPLOAD_DIR = os.environ.get("SHERLOCK_UPLOAD_DIR", None)
"""The relative folder, the uploaded and scraped files should be stored."""
