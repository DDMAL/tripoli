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


class ManifestValidator(BaseValidator):
    VIEW_DIRS = ['left-to-right', 'right-to-left',
                 'top-to-bottom', 'bottom-to-top']
    VIEW_HINTS = ['individuals', 'paged', 'continuous']

    KNOWN_FIELDS = BaseValidator.COMMON_FIELDS | {"viewingDirection", "navDate", "sequences", "structures", "@context"}
    FORBIDDEN_FIELDS = {"format", "height", "width", "startCanvas", "first", "last", "total", "next", "prev",
                        "startIndex", "collections", "manifests", "members", "canvases", "resources", "otherContent",
                        "images", "ranges"}
    REQUIRED_FIELDS = {"label", "@context", "@id", "@type", "sequences"}
    RECOMMENDED_FIELDS = {"metadata", "description", "thumbnail"}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.ManifestSchema = OrderedDict((
            ('@context', self.context_field),
            ('structures', self.structures_field),
            ('sequences', self.sequences_field),
        ))
        self.setup()

    def _run_validation(self, **kwargs):
        self._check_all_key_constraints("manifest", self._json)
        return self._compare_dicts(self.ManifestSchema, self._json)

    def type_field(self, value):
        """Assert that ``@type`` == ``sc:Manifest``. """
        if not value == 'sc:Manifest':
            self.log_error("@type", "@type must be 'sc:Manifest'.")
        return value

    def context_field(self, value):
        """Assert that ``@context`` is the IIIF 2.0 presentation API."""
        if isinstance(value, str):
            if not value == self.PRESENTATION_API_URI:
                self.log_error("@context", "'@context' must be set to '{}'".format(self.PRESENTATION_API_URI))
        if isinstance(value, list):
            if self.PRESENTATION_API_URI not in value:
                self.log_error("@context", "'@context' must be set to '{}'".format(self.PRESENTATION_API_URI))
        return value

    def structures_field(self, value):
        """Validate the ``structures`` field."""
        return value

    def sequences_field(self, value):
        """Validate ``sequences`` list for Manifest.

        Checks that exactly 1 sequence is embedded.
        """
        if not isinstance(value, list):
            self.log_error("sequences", "'sequences' MUST be a list")
            return value

        results = []
        path = self._path + ("sequences",)
        for i, seq in enumerate(value):
            temp_path = path + i
            if i == 0:
                results.append(self._sub_validate(self.SequenceValidator, seq, temp_path, emb=True))
            else:
                results.append(self._sub_validate(self.SequenceValidator, seq, temp_path, emb=False))
        return results
