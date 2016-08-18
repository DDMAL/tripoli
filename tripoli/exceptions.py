class FailFastException(Exception):
    """Raised when validation should end because error is hit."""
    pass


class TypeParseException(Exception):
    """Raised when a `@type` can not be parsed from input data."""
    pass
