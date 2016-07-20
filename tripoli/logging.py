import traceback


class ValidatorLogEntry:
    """Basic error logging lass with comparison behavior for hashing."""

    def __init__(self, msg, path, tb=None):
        self.msg = msg
        self.path = path
        self._tb = tb if tb else []

    def print_trace(self):
        traceback.print_list(self._tb)

    def __lt__(self, other):
        return len(self.path) < len(other.path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)


class ValidatorLogWarning(ValidatorLogEntry):
    """Class to hold and present warnings."""

    def __str__(self):
        path = ' @ data[%s]' % ']['.join(map(repr, self.path)) if self.path else ''
        output = "Warning: {}".format(self.msg)
        return output + path

    def __repr__(self):
        return "ValidatorLogWarning('{}', {})".format(self.msg, self.path)


class ValidatorLogError(ValidatorLogEntry):
    """Class to hold and present errors."""

    def __str__(self):
        path = ' @ data[%s]' % ']['.join(map(repr, self.path)) if self.path else ''
        output = "Error: {}".format(self.msg)
        return output + path

    def __repr__(self):
        return "ValidatorLogError('{}', {})".format(self.msg, self.path)