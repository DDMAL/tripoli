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

from collections import OrderedDict

from .base_validator import BaseValidator


class SequenceValidator(BaseValidator):
    VIEW_DIRS = {'left-to-right', 'right-to-left',
                 'top-to-bottom', 'bottom-to-top'}
    VIEW_HINTS = {'individuals', 'paged', 'continuous'}

    KNOWN_FIELDS = BaseValidator.COMMON_FIELDS | {"viewingDirection", "startCanvas", "canvases"}
    FORBIDDEN_FIELDS = {"format", "height", "width", "navDate", "first", "last", "total", "next", "prev",
                        "startIndex", "collections", "manifests", "sequences", "structures", "resources",
                        "otherContent", "images", "ranges"}
    REQUIRED_FIELDS = {"@type", "canvases"}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.emb = None
        self.EmbSequenceSchema = OrderedDict((
            ('@type', self.type_field),
            ('@context', self.context_field),
            ('@id', self.id_field),
            ('startCanvas', self.startCanvas_field),
            ('viewingDirection', self.viewing_dir_field),
            ('viewingHint', self.viewing_hint_field),
            ('canvases', self.canvases_field),
        ))

        self.LinkedSequenceSchema = OrderedDict((
            ('@type', self.type_field),
            ('@id', self.id_field),
            ('canvases', self._not_allowed)
        ))
        self.setup()

    def _run_validation(self, **kwargs):
        self._check_all_key_constraints("sequence", self._json)
        return self._validate_sequence(**kwargs)

    def _validate_sequence(self, emb=True):
        self.emb = emb
        if self.emb:
            return self._compare_dicts(self.EmbSequenceSchema, self._json)
        else:
            return self._compare_dicts(self.LinkedSequenceSchema, self._json)

    def _raise_additional_warnings(self, validation_results):
        pass

    def type_field(self, value):
        """Assert that ``@type`` == ``sc:Sequence``"""
        if value != "sc:Sequence":
            self.log_error("@type", "@type must be 'sc:Sequence'")
        return value

    def context_field(self, value):
        """Assert that ``@context`` is the IIIF 2.0 presentation API if it is allowed."""
        if self.emb:
            self.log_error("@context", "@context field not allowed in embedded sequence.")
            return value
        if value != self.PRESENTATION_API_URI:
            self.log_error("@context", "unknown context.")
        return value

    def startCanvas_field(self, value):
        """Validate ``startCanvas`` field."""
        return self._uri_type("startCanvas", value)

    def canvases_field(self, value):
        """Validate ``canvases`` list for Sequence."""
        if not isinstance(value, list):
            self.log_error("canvases", "'canvases' MUST be a list.")
            return value
        if len(value) < 1:
            self.log_error("canvases", "'canvases' MUST have at least one entry")
            return value
        path = self._path + ("canvases",)
        return [self._sub_validate(self.CanvasValidator, c, path) for c in value]
