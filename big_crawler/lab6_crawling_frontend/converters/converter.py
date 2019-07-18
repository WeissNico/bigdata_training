"""This module defines a set of converters, which are used to convert the
content to pdf.

Author: Johannes Mueller <j.mueller@reply.de>
"""
from abc import abstractmethod


class BaseConverter:

    def __init__(self):
        super(BaseConverter, self).__init__()

    @abstractmethod
    def convert(self, content, **kwargs):
        """Converts the content into another format.

        Args:
            content (bytes): some content.
            **kwargs (dict): additional parameters used in the implementations
                convert method.

        Returns:
            bytes: content in a different format.
        """

    def __call__(self, content, **additional_args):
        """Converts the content into another format.

        Args:
            content (bytes): some content.
            **additional_args (dict): additional args to pass to the convert
                function.

        Returns:
            bytes: content in a different format.
        """
        ret = self.convert(content, **additional_args)
        return ret


class DummyConverter(BaseConverter):
    """Simple Converter for the pdf-mimetype.

    Just fetches the content and returns it.
    """
    def convert(self, content, **kwargs):
        return content


class EmptyConverter(BaseConverter):
    """Converter that just returns None."""
    def convert(self, content, **kwargs):
        return None
