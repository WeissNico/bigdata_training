"""This module defines a set of analyzers, that work in a similar scheme.

They take a document, described by a dictionary as input, check whether it
already has the required attributes, perform some analyzation task, and
return a extended document.

Author: Johannes Müller <j.mueller@reply.de>
"""
from abc import abstractmethod

import utility as ut


class BaseAnalyzer():
    """Base Class for an analyzer.

    Children must define a list of required attributes.
    """
    required = []
    """List of required string attributes, that should be overridden."""

    def __init__(self):
        super(BaseAnalyzer, self).__init__()

    def __call__(self, doc):
        """Analyzes the given document and returns a set of derived properties.

        Args:
            doc (dict): the dictionary representing the document.

        Returns:
            dict: a dictionary holding new keys.
        """
        self.check_keys(doc)
        processed = self.analyze(ut.filter_dict(doc, self.required))
        return self.merge_doc(doc, processed)

    def check_keys(self, doc):
        """Checks whether all required keys are contained in `doc`.

        Args:
            doc (dict): the dictionary representing the document.

        Raises:
            KeyError
        """
        if not all([key in doc for key in self.required]):
            raise KeyError(f"{self.__name__} needs the following attributes in"
                           f" docs: {' '.join(self.required)}!")

    def merge_doc(self, doc, new_keys):
        """Merges the document with a set of new keys.

        Args:
            doc (dict): the dictionary representing the document.
            new_keys (dict): a dict holding the new keys.

        Returns:
            dict: a merged_dictionary.
        """
        return ut.merge_dicts(doc, new_keys)

    @abstractmethod
    def analyze(self, doc, **options):
        """Perform the analyzation of the given document.

        Args:
            doc (dict): the dictionary representing the document.
            **options (dict): additional options for the analyzation step.

        Returns:
            dict: a newly processed dictionary.
        """


class DefaultAnalyzer(BaseAnalyzer):
    """Analyzer for setting default values."""

    required = []

    def analyze(self, doc, **options):
        return {
            "date": ut.from_date(),
            "source": {
                "url": None,
                "name": "inhouse"
            },
            "hash": None,
            "version": None,
            "content_type": "application/pdf",
            "content": None,
            "document": "No Title",
            "text": "",
            "tags": [],
            "keywords": {},
            "entities": {},
            "quantity": {"lines": 0, "words": 0},
            "change": {"lines_added": 0, "lines_removed": 0},
            "metadata": {},
            "type": "?",
            "category": "?",
            "fingerprint": "a_fingerprint",
            "version_key": None,
            "connections": {},
            "impact": "low",
            "status": "open",
            "new": True,
        }


class TextAnalyzer(BaseAnalyzer):
    """Analyzer for creating the text features."""

    required = ["text"]

    def analyze(self, doc, **options):
        lines, words = ut.calculate_quantity(doc["text"])
        return {
            "quantity": {"lines": lines, "words": words},
            "change": {"lines_added": lines, "lines_removed": 0},
        }


class MetaAnalyzer(BaseAnalyzer):
    """Analyzer for the included metadata."""

    required = ["metadata"]

    def analyze(self, doc, **options):
        doc = ut.SDA(doc)
        return {
            "date": ut.date_from_string(
                ut.try_keys(doc, ["metadata.date", "metadata.ModDate",
                                  "metadata.Last-Modified",
                                  "metadata.modified",
                                  "metadata.CreationDate",
                                  "metadata.crawl_date"],
                            None)),
            "source": {
                "url": doc["metadata.url"],
                "name": doc["metadata.source"] or "inhouse"
            },
            "content_type": ut.try_keys(doc,
                                        ["metadata.contentType",
                                         "metadata.mimetype",
                                         "metadata.Content-Type",
                                         "metadata.dc:format"],
                                        "application/pdf").strip(),
            "document": ut.try_keys(doc,
                                    ["metadata.title",
                                     "metadata.Title",
                                     "metadata.dc:title",
                                     "metadata.filename"],
                                    "No Title").strip()
        }
