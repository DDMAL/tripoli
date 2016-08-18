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


class ImageContentValidator(BaseValidator):
    KNOWN_FIELDS = BaseValidator.COMMON_FIELDS | {"@context", "height", "width", "format"}
    FORBIDDEN_FIELDS = {"viewingDirection", "navDate", "startCanvas", "first", "last", "total",
                        "next", "prev", "startIndex", "collections", "manifests", "members",
                        "sequences", "structures", "canvases", "resources", "otherContent",
                        "images", "ranges"}
    REQUIRED_FIELDS = {'@type', '@id'}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.ImageContentSchema = OrderedDict((
            ('@id', self.id_field),
            ('@type', self.type_field),
            ('height', self.height_field),
            ('width', self.width_field),
            ('service', self.service_field)
        ))
        self.setup()

    def _run_validation(self, **kwargs):
        self._check_all_key_constraints("resource", self._json)
        return self._compare_dicts(self.ImageContentSchema, self._json)

    def type_field(self, value):
        """Warn if ``@type != 'dctypes:Image'``"""
        if value != 'dctypes:Image':
            self.log_error('@type', "@type MUST be \'dctypes:Image\'")
        return value

    def service_field(self, value):
        """Validate the image service in this resource."""
        with self._temp_path(self._path + ('service',)):
            self._check_required_fields("image service", value, ['@id', '@context'])
            self._check_recommended_fields("image service", value, ['profile'])
            context = value.get("@context")
            if context and context != self.IMAGE_API_2:
                if context != self.IMAGE_API_1:
                    self.log_error('@context', "Must reference IIIF image API.")
                else:
                    self.log_warning('@context', "SHOULD upgrade to 2.0 IIIF image service.")
            return value
