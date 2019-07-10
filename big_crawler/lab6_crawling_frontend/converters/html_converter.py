"""This module defines a converter for converting a arbitrary office file to
pdf.

Author: Johannes Mueller <j.mueller@reply.de>
"""
import re
from urllib.parse import urljoin

import pdfkit
from lxml import etree, html

import utility
import logging

from crawlers.plugin import XPathResource
from converters.converter import BaseConverter


logger = logging.getLogger(__name__)


class HTMLConverter(BaseConverter):
    """Simple Converter for the html mime-type.

    Just fetches the content and converts it using wkhtmltopdf.
    """
    def __init__(self, content_xpath=None):
        """Initializes the HTML converter.

        Args:
            content_xpath (etree.XPath): an XPath pointing to the relevant
                html portions. Defaults to `//body`
                for fetching all the contents of the page.
        """
        super().__init__()

        self.content_xpath = content_xpath
        if content_xpath is None:
            self.content_xpath = XPathResource(
                "//body"
            )
        self.head_xpath = XPathResource(
            "//head"
        )
        self.link_xpath = XPathResource(
            "//*[@href or @src]"
        )
        self.style_xpath = XPathResource(
            "//style[@type = 'text/css' and contains(text(), 'url(')]"
        )
        self.base_xpath = XPathResource(
            "//head/base/@href",
            after=[utility.defer("__getitem__", 0)]
        )
        # treat windows specially
        if utility.PLATFORM == "win32":
            self.pdfkit_config = pdfkit.configuration(
                wkhtmltopdf=utility.path_in_project("wkhtmltopdf", True)
            )
        else:
            self.pdfkit_config = pdfkit.configuration()

    def _replace_relative(self, tree, base_url):
        """Replaces relative href and src attributes.

        Args:
            tree (lxml.etree): An html-ETree.
            base_url (str): the base url.
        """
        def _replace_css_url(match):
            return (match.group(1) + urljoin(base_url, match.group(2)) +
                    match.group(3))

        # replace in the attributes
        for elem in self.link_xpath(tree):
            for attr in ["href", "src"]:
                if attr not in elem.attrib:
                    continue
                elem.attrib[attr] = urljoin(base_url, elem.attrib[attr])
        # replace in css
        for elem in self.style_xpath(tree):
            elem.text = re.sub(r"(url\()([^\)]+)(\))", _replace_css_url,
                               elem.text)
            links = re.findall(r"url\(([^\)]+)\)", elem.text)
            for link in links:
                elem.addnext(
                    etree.XML(f"<link rel='stylesheet' href='{link}' />")
                )

    def convert(self, content, **kwargs):
        tree = html.fromstring(content)
        # retrieve base url from kwargs
        base_url = kwargs.get("base_url", None)
        base_url_found = self.base_xpath(tree)
        if base_url_found:
            base_url = base_url_found
        # replace relative links
        self._replace_relative(tree, base_url)
        relevant_html = self.head_xpath(tree)
        relevant_html.extend(self.content_xpath(tree))
        # stringify the portions together
        html_string = "\n".join([html.tostring(part).decode("utf-8")
                                 for part in relevant_html])
        try:
            doc = pdfkit.from_string(html_string, False,
                                     configuration=self.pdfkit_config)
        except IOError as ioe:
            logger.warning("Skipped a document due to wkhtmltopdf failure.")
            return None
        return doc
