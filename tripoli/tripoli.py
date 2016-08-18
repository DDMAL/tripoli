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

import json
import logging

from .exceptions import FailFastException
from .mixins import SubValidationMixin
from .validator_logging import ValidatorLogError, ValidatorLog
from .resource_validators import (
    ManifestValidator, SequenceValidator, CanvasValidator,
    ImageContentValidator, AnnotationValidator)

__version__ = "1.1"


class IIIFValidator(SubValidationMixin):
    def __init__(self):
        super().__init__()
        self._ManifestValidator = None
        self._AnnotationValidator = None
        self._CanvasValidator = None
        self._SequenceValidator = None
        self._ImageContentValidator = None

        #: ``logging.getLogger()`` used to print output.
        self.logger = logging.getLogger("tripoli")

        #: Sets whether or not to save tracebacks in warnings/errors.
        #: Default ``False``.
        self.debug = False

        #: Sets whether or not warnings are logged.
        #: Default ``True``.
        self.collect_warnings = True

        #: Sets whether or not errors are logged.
        #: Default ``True``.
        self.collect_errors = True

        #: When ``True``, validation stops at first error hit (faster).
        #: If ``False``, entire document will always be validated.
        #: Default ``True``.
        self.fail_fast = True

        #: If corrections were made during validation, the corrected document
        #: will be placed here.
        self.corrected_doc = {}

        #: If ``True``, prints all errors and warnings as they occur.
        #: If ``False``, errors and warnings only printed after de-duplication.
        #: Default ``False``.
        self.verbose = False

        #: If ``True``, only one instance of duplicate logged messages will be saved.
        #: If ``False``, all logged messages will be saved.
        #: Default ``True``.

        #: Example: If set to true, then if every canvas has error A, instead
        #: of having the errors (Error(A, canvas[0]), Error(A, canvas[1]), ...), you
        #: will only get Error(A, canvas[0]) (the first error of type A on a canvas).
        self.unique_logging = True

        self._setup_to_validate()

    @property
    def ManifestValidator(self):
        """An instance of a ManifestValidator."""
        return self._ManifestValidator

    @property
    def SequenceValidator(self):
        """An instance of a SequenceValidator."""
        return self._SequenceValidator

    @property
    def CanvasValidator(self):
        """An instance of a CanvasValidator."""
        return self._CanvasValidator

    @property
    def AnnotationValidator(self):
        """An instance of an AnnotationValidator"""
        return self._AnnotationValidator

    @property
    def ImageContentValidator(self):
        """An instance of an ImageContentValidator"""
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
        self._errors = ValidatorLog(self.unique_logging)
        self._warnings = ValidatorLog(self.unique_logging)
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
