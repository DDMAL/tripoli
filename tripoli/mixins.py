class LinkedValidatorMixin:
    """Basic support for storing 'global' references in a single administrative class."""

    def __init__(self, iiif_validator=None):
        self._IIIFValidator = iiif_validator

    @property
    def collect_warnings(self):
        return self._IIIFValidator.collect_warnings

    @property
    def collect_errors(self):
        return self._IIIFValidator.collect_errors

    @property
    def debug(self):
        return self._IIIFValidator.debug

    @property
    def fail_fast(self):
        return self._IIIFValidator.fail_fast

    @property
    def ManifestValidator(self):
        return self._IIIFValidator._ManifestValidator

    @property
    def SequenceValidator(self):
        return self._IIIFValidator._SequenceValidator

    @property
    def CanvasValidator(self):
        return self._IIIFValidator._CanvasValidator

    @property
    def AnnotationValidator(self):
        return self._IIIFValidator._AnnotationValidator

    @property
    def ImageContentValidator(self):
        return self._IIIFValidator._ImageContentValidator


class SubValidationMixin:
    """Provides needed parts to accumulate errors and delegate validation."""

    def __init__(self):
        self._errors = set()
        self._warnings = set()
        self.is_valid = None

    @property
    def errors(self):
        return list(self._errors)

    @property
    def warnings(self):
        return list(self._warnings)

    def print_errors(self):
        """Print the errors in a nice format."""
        for err in self._errors:
            print(err)

    def print_warnings(self):
        """Print the warnings in a nice format."""
        for warn in self._warnings:
            print(warn)

    def _sub_validate(self, subschema, value, path, **kwargs):
        """Validate a field using another Validator.

        :param subschema: A BaseValidator implementing object.
        :param value (dict): The data to be validated.
        :param path (tuple): The path where the above data exists.
            Example: ('sequences', 'canvases') for the CanvasValidator.
        :param kwargs: Any keys to subschema._run_validation()
            - canvas_uri: String passed to AnnotationValidator from
              CanvasValidator to ensure 'on' key is valid.
            - raise_warnings: bool to decide if warnings will be recorded
              or not.
        """
        try:
            subschema._validate(value, path, **kwargs)
        finally:
            if subschema._errors:
                self._errors = self._errors | subschema._errors
            if subschema._warnings:
                self._warnings = self._warnings | subschema._warnings
            if subschema.corrected_doc:
                return subschema.corrected_doc
            else:
                return subschema._json
