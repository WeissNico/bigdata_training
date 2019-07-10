from .converter import EmptyConverter, DummyConverter

from .html_converter import HTMLConverter
from .office_converter import OfficeConverter

CONVERTERS = {
    "application/pdf": DummyConverter(),
    "text/html": HTMLConverter(),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        OfficeConverter(),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        OfficeConverter(),
    "application/msword": OfficeConverter(),
    "application/msexcel": OfficeConverter(),
    "application/mspowerpoint": OfficeConverter(),
    "application/vnd.oasis.opendocument.text": OfficeConverter(),
    "application/vnd.oasis.opendocument.spreadsheet": OfficeConverter(),
    "application/vnd.oasis.opendocument.presentation": OfficeConverter(),
}

CONVERTERS.setdefault(EmptyConverter)
