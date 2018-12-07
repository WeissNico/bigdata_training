"""File storage module, which abstracts the interaction with the hard drive.

This is put in a seperate module, such that it can be swapped for some more
scalable solution later.

Author: Johannes Müller <j.mueller@reply.de>
"""

import os
import hashlib
import logging

import utility

logger = logging.getLogger(__name__)


def _create_dir(dirpath):
    """Creates a directory if it's not already existant.

    Args:
        dirpath (str): the path to the directory.

    Returns:
        bool: True when directory is ready to use, False otherwise.
    """
    if not os.path.exists(dirpath):
        try:
            os.makedirs(dirpath)
        except IOError as ioe:
            logger.error(f"IOError occured, while trying to create {dirpath}")
            return False
    return True


def _hash_content(content):
    """Returns a sha256-hash of the content.

    Args:
        content (bytes): the file contents.

    Returns:
        str: the files sha256-hash
    """
    hash_obj = hashlib.sha256(content)
    return hash_obj.hexdigest()


class FileStore():
    """The filestore simply takes contents and saves them to file.

    For saving space they are saved using the sha256 hashes as filenames.
    """

    def __init__(self, directory=None):
        """Initialize a file-store to the given directory.

        Args:
            directory (str): an absolute directory, where the files should be
                saved.
        """
        self.defaults = utility.DefaultDict({
            "mode": "b"
        })
        self.dir = directory

        # set a default path
        if self.dir is None:
            self.dir = utility.path_in_project("uploads")

        if not _create_dir(self.dir):
            raise IOError(f"Couldn't create the upload folder: {self.dir}")

    def set(self, content, mode="b"):
        """Saves the given content into a file.

        The filename will equal the hash of the content, if the file is already
        saved, just return the bytes object.

        Args:
            content (bytes): a bytes object.
            mode (str): 'b' binary or 't' text reading mode. Defaults to 'b'.

        Returns:
            str: the relative name of this file.
        """
        mode = self.defaults.mode.also(mode)

        filename = _hash_content(content)
        path = os.path.join(self.dir, filename)
        # early exit, when file path does already exist.
        if os.path.exists(path):
            return filename

        with open(path, "w" + mode) as fl:
            fl.write(content)

        logger.debug(f"Created file '{filename}'.")
        return filename

    def get(self, filename, mode="b"):
        """Returns the content of the given file.

        Args:
            filename (str): the filename (hash) of the file.
            mode (str): 'b' binary or 't' text reading mode. Defaults to 'b'.

        Returns:
            bytes: the contents of the file.
        """
        mode = self.defaults.mode.also(mode)

        if filename is None or len(filename) == 0:
            return None

        path = os.path.join(self.dir, filename)
        contents = None

        try:
            with open(path, "r" + mode) as fl:
                contents = fl.read()
        except EnvironmentError as ee:
            pass

        return contents

    def remove(self, filename):
        """Removes a file from the file-store.

        Args:
            filename (str): the filename (hash) of the file.

        Returns:
            bool: True when the deletion succeeded, False otherwise.
        """
        path = os.path.join(self.dir, filename)

        try:
            os.remove(path)
        except IOError as ioe:
            logger.error(f"Failed to delete file '{path}'.")
            return False

        logger.debug(f"Deleted file '{path}'.")
        return True
