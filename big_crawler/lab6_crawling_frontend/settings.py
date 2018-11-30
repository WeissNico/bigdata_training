"""This little module contains all settings regarding our app."""

import logging
import os

ELASTICSEARCH_USER = "admin"
ELASTICSEARCH_PASSWORT = "RYZUAYORFMEGJRCT"
ELASTICSEARCH_HOST = ("portal-ssl223-11.bmix-lon-yp-2012af18-4749-4d32-94a6-"
                      "09573ff5ee35.3259324498.composedb.com")
ELASTICSEARCH_PORT = 26611
LOGGING_LEVEL = logging.DEBUG

SECRET_KEY = os.environ.get("SHERLOCK_SECRET", "pl34se change th1s!")
"""The secret key for csrf-protection and so on. Please change."""

UPLOAD_DIR = os.environ.get("SHERLOCK_UPLOAD_DIR", "uploads")
"""The relative folder, the uploaded and scraped files should be stored."""
