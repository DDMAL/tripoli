# Copyright (c) 2016 Alex Parmentier, Andrew Hankinson

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import traceback
from itertools import zip_longest


class Path:
    """Class representing path within document."""
    def __init__(self, path):
        """ Create a Path.

        :param path: Tuple of strings and ints.
        """
        self._path = path
        self.__no_index_path = None

    def __eq__(self, other):
        return self._path == other._path

    def __len__(self):
        return len(self._path)

    def __str__(self):
        return ' @ data[%s]' % ']['.join(map(repr, self._path)) if self._path else ''

    def __repr__(self):
        return 'Path({})'.format(", ".join(repr(x) for x in self._path))

    def __iter__(self):
        return self._path.__iter__()

    def __add__(self, other):
        if isinstance(other, (str, int)):
            return Path(self._path + (other,))
        if isinstance(other, tuple):
            return Path(self._path + other)
        if isinstance(other, Path):
            return Path(self._path + other._path)
        raise NotImplemented

    def __hash__(self):
        return hash(self._path)

    @property
    def no_index_path(self):
        if self.__no_index_path is None:
            self.__no_index_path = tuple(filter(lambda x: isinstance(x, str), self._path))
        return self.__no_index_path

    @property
    def path(self):
        return self._path

    def no_index_eq(self, other):
        """Return true if paths are the same, ignoring indexes.

        Useful for hashing, as we typically only care about storing
        one instance of each error/warning per list.
        """
        return self.no_index_path == other.no_index_path

    def no_index_endswith(self, path):
        """Return true is self.no_index_path has ``path`` as a suffix.

        :param path: Either a str-tuple or a Path.
        """
        if isinstance(path, Path):
            path = path.no_index_path
        for a, b in zip_longest(reversed(self.no_index_path), reversed(path)):
            if b is None:
                return True
            if a != b:
                return False
        return True


class ValidatorLog:
    """Log which provides unified interface for either set or list like behaviour."""
    def __init__(self, unique_logging=True):
        self.unique_logging = unique_logging
        self._entries = set() if unique_logging else []

    def add(self, log_entry):
        """Add an entry to the log.

        :param log_entry: A ValidatorLogEntry to add to self.
        """
        if isinstance(log_entry, ValidatorLogEntry):
            if self.unique_logging:
                self._entries.add(log_entry)
            else:
                self._entries.append(log_entry)
        else:
            raise TypeError('log_entry must be a ValidatorLogEntry')

    def update(self, log_entry):
        """Add all entries from log_entry to self.

        :param log_entry: A ValidatorLog to update from.
        """
        for entry in log_entry._entries:
            self.add(entry)

    def __iter__(self):
        return iter(self._entries)

    def __bool__(self):
        return bool(self._entries)


class ValidatorLogEntry:
    """Basic error logging class with comparison behavior for hashing."""

    def __init__(self, msg, path, tb=None):
        """

        :param msg: A message associated with the log entry.
        :param path: A tuple representing the path where entry was logged.
        :param tb: A traceback.extract_stack() list from the point entry was logged.
        """

        #: A message associated with the log entry.
        self.msg = msg

        #: A tuple representing the path where the entry was created.
        self.path = Path(path)

        self._tb = tb if tb else []

    def print_trace(self):
        """Print the stored traceback if it exists."""
        traceback.print_list(self._tb)

    def path_str(self):
        return str(self.path)

    def log_str(self):
        return self.msg + self.path_str()

    def __lt__(self, other):
        return len(self.path) < len(other.path)

    def __hash__(self):
        return hash(str(self.path.no_index_path) + self.msg)

    def __eq__(self, other):
        return self.path.no_index_path == other.path.no_index_path\
                and self.msg == other.msg


class ValidatorLogWarning(ValidatorLogEntry):
    """Class to hold and present warnings."""

    def __str__(self):
        output = "Warning: {}".format(self.msg)
        return output + self.path_str()

    def __repr__(self):
        return "ValidatorLogWarning('{}', {})".format(self.msg, self.path)


class ValidatorLogError(ValidatorLogEntry):
    """Class to hold and present errors."""

    def __str__(self):
        output = "Error: {}".format(self.msg)
        return output + self.path_str()

    def __repr__(self):
        return "ValidatorLogError('{}', {})".format(self.msg, self.path)
