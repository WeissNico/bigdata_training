"""This module provides the class PDFAnalyzer, for reading in PDF-Documents.

It provides functionallity to extract all necessary metadata from a PDF-File
and process it such that it fits into our elasticsearch db.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import io
import os
import subprocess
import tempfile
import datetime as dt
import logging
import shutil
import xml  # just for that one stupid error :/
from PyPDF2 import PdfFileReader

import utility
from analyzers.analyzer import BaseAnalyzer

XMP_NAMESPACES = {
    "http://purl.org/dc/elements/1.1/": "dc",
    "http://ns.adobe.com/xap/1.0/": "xmp",
    "http://ns.adobe.com/xap/1.0/mm/": "xmpMM",
    "http://ns.adobe.com/pdf/1.3/": "pdf",
    "http://ns.adobe.com/xap/1.0/t/pg/": "xmpTPg"
}


def _datetime_from_meta_string(datestring):
    """Returs a datetime from a string as given in the PDFs metadata.

    Format example: `D:20180910171244+03'00`
    alternatively: `D:20180910171244`

    Args:
        datestring (str): a date in string-format.

    Return:
        datetime.datetime: a valid python datetime.
    """
    this_date = None
    # replace the ' character with none, to make the docInfo string
    # conforming to %z (UTC-Offset)
    without_apo = datestring.replace("'", "")

    try:
        this_date = dt.datetime.strptime(without_apo, "D:%Y%m%d%H%M%S%z")
    except ValueError:
        pass

    try:
        this_date = dt.datetime.strptime(without_apo, "D:%Y%m%d%H%M%S")
    except ValueError:
        pass

    return this_date


class PDFAnalyzer(BaseAnalyzer):

    required = ["content"]

    def __init__(self, **kwargs):
        """Initializes the PDFAnalyzer with an `elastic.Elastic` instance.

        Args:
            **kwargs (dict): keyword-arguments for further options.

        Returns:
            PDFConverter: a new PDFConverter instance.
        """
        super().__init__()
        self.defaults = utility.DefaultDict({
            "bin_path": utility.path_in_project("pdftotext", True)
        }, **kwargs)

    def _convert_pdf(self, content, exc, tmp_pdf, tmp_txt, **kwargs):
        """Converts a binary pdf-stream to text, by using xpdf utilties.

        Saves the `stream` in `tmp_pdf` and converts to `tmp_txt`."""
        # get a password if saved
        password = self.defaults.other(kwargs).password()
        # save the stream to the temporary files
        with open(tmp_pdf, "wb") as fl:
            fl.write(content)

        arguments = [exc, "-enc", "UTF-8"]
        if password is not None:
            arguments += ["-upw", password]
        process = subprocess.Popen(arguments + [tmp_pdf, tmp_txt])
        ret = process.wait()
        if ret != 0:
            raise IOError("Couldn't extract any text information.")
        return ret

    def _pdftotext(self, content, **kwargs):
        """Returns the contained text of the PDF-File."""
        # get the path to the executable
        path_to_exc = self.defaults.bin_path()
        if not (os.path.exists(path_to_exc) or shutil.which(path_to_exc)):
            raise ValueError(f"The current path '{path_to_exc}' does not lead "
                             " to an actual file.")
        text = None
        # get the temporary paths
        try:
            with tempfile.TemporaryDirectory(prefix=".pdfconv_") as tmp_dir:
                tmp_pdf = os.path.join(tmp_dir, "input.pdf")
                tmp_txt = os.path.join(tmp_dir, "output.txt")

                self._convert_pdf(content, path_to_exc, tmp_pdf, tmp_txt,
                                  **kwargs)

                # read back the write results
                try:
                    with open(tmp_txt, "r", encoding="utf-8") as fl:
                        text = fl.read()
                except UnicodeDecodeError as e:
                    with open(tmp_txt, "r", encoding="latin-1") as fl:
                        text = fl.read()
        # handle an OSError (could surface because of AntiVir)
        except OSError as ose:
            logging.error("Supressed an OSError while handling the "
                          " temp-folder.")
        return text

    def _getpdfmeta(self, content, **kwargs):
        """Returns a dict containing the pdfs-metadata."""
        # other possible implementations
        # https://stackoverflow.com/questions/14209214/reading-the-pdf-properties-metadata-in-python
        # http://blog.matt-swain.com/post/25650072381/a-lightweight-xmp-parser-for-extracting-pdf
        password = self.defaults.other(kwargs).password("")
        filename = self.defaults.other(kwargs).filename("No Filename")

        metadata = {
            "filename": filename,
        }

        pdf = PdfFileReader(io.BytesIO(content))
        if pdf.isEncrypted:
            try:
                result = pdf.decrypt(password)
            except NotImplementedError:
                result = 0
            # skip when document couldn't be decrypted.
            if result == 0:
                return metadata
        # retrieve the info documents
        doc_info = pdf.getDocumentInfo()
        try:
            doc_xmp = pdf.getXmpMetadata()
        except xml.parsers.expat.ExpatError as e:
            doc_xmp = None

        # and create a nice dict, in the form that nutch provides.
        # for the doc info...
        if doc_info is not None:
            for key, value in doc_info.items():
                if "Date" in key:
                    # use str in order to dereference IndirectObjects
                    metadata[key[1:]] = _datetime_from_meta_string(str(value))
                else:
                    metadata[key[1:]] = str(value)

        # go through the XMP-namespaces and add the properties.
        if doc_xmp is not None:
            for ns, keys in doc_xmp.cache.items():
                prefix = XMP_NAMESPACES.get(ns, "meta")
                for key, value in keys.items():
                    val = utility.clean_value(value)
                    if val is not None:
                        metadata[f"{prefix}:{key}"] = val

        return metadata

    def analyze(self, doc, **kwargs):
        # skip empty documents
        if doc["content"] is None:
            return doc
        meta = self._getpdfmeta(doc["content"], **kwargs)
        text = self._pdftotext(doc["content"], **kwargs)

        merge_doc = {
            "text": text,
            "metadata": meta
        }

        return merge_doc
