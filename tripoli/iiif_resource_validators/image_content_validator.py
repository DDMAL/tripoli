from collections import OrderedDict

from .base_validator import BaseValidator


class ImageContentValidator(BaseValidator):
    KNOWN_FIELDS = BaseValidator.COMMON_FIELDS | {"@context", "height", "width", "format"}
    FORBIDDEN_FIELDS = {"viewingDirection", "navDate", "startCanvas", "first", "last", "total",
                        "next", "prev", "startIndex", "collections", "manifests", "members",
                        "sequences", "structures", "canvases", "resources", "otherContent",
                        "images", "ranges"}
    REQUIRED_FIELDS = {'@type'}
    RECOMMENDED_FIELDS = {'@id', 'profile'}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.ImageContentSchema = OrderedDict((
            ('@id', self.id_field),
            ('@type', self.type_field),
            ('height', self.height_field),
            ('width', self.width_field),
            ('service', self.service_field)
        ))

    def _run_validation(self, **kwargs):
        self._check_all_key_constraints("resource", self._json)
        return self._compare_dicts(self.ImageContentSchema, self._json)

    def height_field(self, value):
        if not isinstance(value, int):
            self.log_error("height", "height must be int.")
        return value

    def width_field(self, value):
        if not isinstance(value, int):
            self.log_error("width", "width must be int.")
        return value

    def type_field(self, value):
        if value != 'dctypes:Image':
            self.log_warning('@type', "@type SHOULD be \'dctypes:Image\'")
        return value

    def service_field(self, value):
        with self._temp_path(self._path + ('service',)):
            self._check_required_fields("image", value, ['@id', '@context'])
            self._check_recommended_fields("image", value, ['profile'])
            context = value.get("@context")
            if context != self.IMAGE_API_2:
                if context != self.IMAGE_API_1:
                    self.log_error('@context', "Must reference IIIF image API.")
                else:
                    self.log_warning('@context', "SHOULD upgrade to 2.0 IIIF image service.")
            return value