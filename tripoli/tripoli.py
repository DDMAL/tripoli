import json
import logging

from tripoli.iiif_resource_validators.base_validator import FailFastException
from tripoli.mixins import SubValidationMixin
from tripoli.logging import ValidatorLogError
from tripoli.iiif_resource_validators import (
    ManifestValidator, SequenceValidator, CanvasValidator,
    ImageContentValidator, AnnotationValidator)


class IIIFValidator(SubValidationMixin):
    def __init__(self):
        super().__init__()
        self._ManifestValidator = None
        self._AnnotationValidator = None
        self._CanvasValidator = None
        self._SequenceValidator = None
        self._ImageContentValidator = None
        self.logger = logging.getLogger("tripoli")
        self.debug = False
        self.collect_warnings = True
        self.collect_errors = True
        self.fail_fast = True
        self._setup_to_validate()

    @property
    def ManifestValidator(self):
        return self._ManifestValidator

    @property
    def SequenceValidator(self):
        return self._SequenceValidator

    @property
    def CanvasValidator(self):
        return self._CanvasValidator

    @property
    def AnnotationValidator(self):
        return self._AnnotationValidator

    @property
    def ImageContentValidator(self):
        return self._ImageContentValidator

    @ManifestValidator.setter
    def ManifestValidator(self, value):
        self._ManifestValidator = value(self)

    @SequenceValidator.setter
    def SequenceValidator(self, value):
        self._SequenceValidator = value(self)

    @CanvasValidator.setter
    def CanvasValidator(self, value):
        self._CanvasValidator = value(self)

    @AnnotationValidator.setter
    def AnnotationValidator(self, value):
        self._AnnotationValidator = value(self)

    @ImageContentValidator.setter
    def ImageContentValidator(self, value):
        self._ImageContentValidator = value(self)

    def _setup_to_validate(self):
        """Make sure all links to sub validators exist."""
        if not self._ManifestValidator:
            self._ManifestValidator = ManifestValidator(self)
        if not self._AnnotationValidator:
            self._AnnotationValidator = AnnotationValidator(self)
        if not self._CanvasValidator:
            self._CanvasValidator = CanvasValidator(self)
        if not self._SequenceValidator:
            self._SequenceValidator = SequenceValidator(self)
        if not self._ImageContentValidator:
            self._ImageContentValidator = ImageContentValidator(self)

        self._TYPE_MAP = {
            "sc:Manifest": self._ManifestValidator,
            "sc:Sequence": self._SequenceValidator,
            "sc:Canvas": self._CanvasValidator,
            "oa:Annotation": self._AnnotationValidator
        }
        self._errors = set()
        self._warnings = set()
        self.corrected_doc = {}

    def _set_from_sub(self, sub):
        """Set the validation attributes to those of a sub_validator.

        Called after sub_validate'ing with validator sub.

        :param sub: A BaseValidator implementing Validator.
        """
        self.is_valid = sub.is_valid
        self.corrected_doc = sub.corrected_doc

    def _output_logging(self):
        """Sends errors and warnings to the logger."""
        for err in self.errors:
            self.logger.error(err.log_str())
        for warn in self.warnings:
            self.logger.warning(warn.log_str())

    def validate(self, json_dict, **kwargs):
        """Determine the correct validator and validate a resource.

        :param json_dict: A dict or str of a json resource.
        """
        self._setup_to_validate()
        if isinstance(json_dict, str):
            try:
                json_dict = json.loads(json_dict)
            except ValueError:
                self._errors.add(ValidatorLogError("Could not parse json.", tuple()))
                self.is_valid = False

        doc_type = json_dict.get("@type")
        validator = self._TYPE_MAP.get(doc_type)
        if not validator:
            self._errors.add(ValidatorLogError("Unknown @type: '{}'".format(doc_type), tuple()))
            self.is_valid = False
        try:
            self._sub_validate(validator, json_dict, path=None, **kwargs)
        except FailFastException:
            pass
        self._set_from_sub(validator)
        self._output_logging()
