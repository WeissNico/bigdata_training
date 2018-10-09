"""This module provides the class PDFConverter, for reading in PDF-Documents.

It provides functionallity to extract all necessary metadata from a PDF-File
and process it such that it fits into our elasticsearch db.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import os
import sys
import subprocess
import tempfile
import datetime as dt

from PyPDF2 import PdfFileReader

import utility

DIR = os.path.dirname(__file__)
PLATFORM = sys.platform

EXEC_SUFFIXES = {
    "win32": ".exe",
    "cygwin": ".exe",
    "linux": "",
    "darwin": ""
}

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


class PDFConverter():

    def __init__(self, elastic, **kwargs):
        """Initializes the PDFConverter with an `elastic.Elastic` instance.

        Args:
            elastic (elastic.Elastic): an elasticsearch connection.
            **kwargs (dict): keyword-arguments for further options.

        Returns:
            PDFConverter: a new PDFConverter instance.
        """
        # construct a default dictionary
        self._defaults = dict({
            "tmp_path": os.path.join(DIR, "tmp"),
        }, **kwargs)
        self.defaults = utility.DefaultDict(self._defaults)
        self.elastic = elastic

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
        path_to_exc = os.path.join(DIR, "bin", PLATFORM,
                                   f"pdftotext{EXEC_SUFFIXES[PLATFORM]}")
        text = None
        # get the temporary paths
        with tempfile.TemporaryDirectory(prefix=".pdfconv_") as tmp_dir:
            tmp_pdf = os.path.join(tmp_dir, "input.pdf")
            tmp_txt = os.path.join(tmp_dir, "output.txt")

            self._convert_pdf(content, path_to_exc, tmp_pdf, tmp_txt, **kwargs)

            # read back the write results
            with open(tmp_txt, "r", encoding="utf-8") as fl:
                text = fl.read()
        return text

    def _getpdfmeta(self, stream, **kwargs):
        """Returns a dict containing the pdfs-metadata."""
        # other possible implementations
        # https://stackoverflow.com/questions/14209214/reading-the-pdf-properties-metadata-in-python
        # http://blog.matt-swain.com/post/25650072381/a-lightweight-xmp-parser-for-extracting-pdf
        password = self.defaults.other(kwargs).password()
        filename = self.defaults.other(kwargs).filename("No Title")
        mimetype = self.defaults.other(kwargs).mimetype("application/pdf")
        pdf = PdfFileReader(stream)
        if pdf.isEncrypted:
            pdf.decrypt(password)
        # retrieve the info documents
        doc_info = pdf.getDocumentInfo()
        doc_xmp = pdf.getXmpMetadata()

        metadata = {
            "crawl_date": utility.from_date(),
            "filename": filename,
            "mimetype": mimetype
        }

        # and create a nice dict, in the form that nutch provides.
        # for the doc info...
        if doc_info is not None:
            for key, value in doc_info.items():
                if "Date" in key:
                    metadata[key[1:]] = _datetime_from_meta_string(value)
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

    def read_stream(self, stream, save=False, **kwargs):
        """Reads and analyzes a pdf-file given as a stream.

        If save flag is set, immediately saves it into the elasticsearch DB.

        Args:
            stream (): the bytes of the pdf-file.
            save (boolean): whether the data should be written through into
                the elastic DB.

        Returns:
            A dictionary holding all relevant information about this text file.
        """
        meta = self._getpdfmeta(stream, **kwargs)
        # reread the stream
        stream.seek(0)
        content = stream.read()
        text = self._pdftotext(content, **kwargs)

        doc = {
            "content": content,
            "text": text,
            "metadata": meta
        }

        res = doc
        if save is True:
            res = self.elastic.insert_document(doc)

        return res

    def read_file(self, path_to_file, save=False, **kwargs):
        """Reads and analyzes a pdf-file from disk.

        If save flag is set, immediately saves it into the elasticsearch DB.

        Args:
            path_to_file (str): the path to the pdf-file.
            save (boolean): whether the data should be written through into
                the elastic DB.

        Returns:
            A dictionary holding all relevant information about this text file.
        """
        with open(path_to_file, "rb") as handle:
            return self.read_stream(handle, save, **kwargs)
