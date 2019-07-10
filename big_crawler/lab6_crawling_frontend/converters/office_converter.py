"""This module defines a converter for converting a arbitrary office file to
pdf.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import os
import shutil
import subprocess
import tempfile

import utility
import logging

from converters.converter import BaseConverter


logger = logging.getLogger(__name__)


class OfficeConverter(BaseConverter):
    """Simple Converter for all LibreOffice-Supported formats.

    Uses an headless libreoffice executable.
    """
    def convert(self, content, **kwargs):
        path_to_exc = utility.path_in_project("soffice", True)
        if not (os.path.exists(path_to_exc) or shutil.which(path_to_exc)):
            raise ValueError(f"The current path '{path_to_exc}' does not lead "
                             " to an actual file.")

        pdf = None
        try:
            with tempfile.TemporaryDirectory(prefix=".officeconv_") as tmp_dir:
                tmp_off = os.path.join(tmp_dir, "office")

                pdf = self._convert_to_pdf(content, path_to_exc, tmp_off,
                                           **kwargs)
        # catch oserrors caused by anti-virus software.
        except OSError as ose:
            logging.error("Supressed an OSError while handling the "
                          " temp-folder.")
        return pdf

    def _convert_to_pdf(self, content, executable, tmp_off, **kwargs):
        with open(tmp_off, "wb") as in_file:
            in_file.write(content)

        command = [executable,
                   "-convert-to pdf",  # target format
                   "-headless",  # headless mode for conversion
                   tmp_off]

        logging.info(f"Running command '{' '.join(command)}'")
        process = subprocess.Popen(command)

        ret = process.wait()
        if ret != 0:
            raise IOError("Couldn't extract any text information.")

        content = None
        tmp_pdf = f"{tmp_off}.pdf"
        with open(tmp_pdf, "rb") as out_file:
            content = out_file.read()
        return content
