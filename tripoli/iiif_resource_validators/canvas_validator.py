from collections import OrderedDict

from tripoli.iiif_resource_validators.base_validator import BaseValidator


class CanvasValidator(BaseValidator):
    VIEW_HINTS = {'non-paged', 'facing-pages'}

    KNOWN_FIELDS = BaseValidator.COMMON_FIELDS | {"height", "width", "otherContent", "images"}
    FORBIDDEN_FIELDS = {"format", "viewingDirection", "navDate", "startCanvas", "first", "last", "total",
                        "next", "prev", "startIndex", "collections", "manifests", "members", "sequences",
                        "structures", "canvases", "resources", "ranges"}
    REQUIRED_FIELDS = {"label", "@id", "@type", "height", "width"}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.CanvasSchema = OrderedDict((
            ('@id', self.id_field),
            ('@type', self.type_field),
            ('label', self.label_field),
            ('height', self.height_field),
            ('width', self.width_field),
            ('viewingHint', self.viewing_hint_field),
            ('other_content', self.other_content_field),
            ('images', self.images_field)
        ))

    def _run_validation(self, **kwargs):
        self.canvas_uri = self._json['@id']
        self._check_all_key_constraints("canvas", self._json)
        return self._compare_dicts(self.CanvasSchema, self._json)

    def _raise_additional_warnings(self, validation_results):
        # Canvas should have a thumbnail if it has multiple images.
        if len(validation_results.get('images', [])) > 1 and not validation_results.get("thumbnail"):
            self.log_warning("thumbnail", "Canvas SHOULD have a thumbnail when there is more than one image")

    def type_field(self, value):
        if value != "sc:Canvas":
            self.log_error("@type", "@type must be 'sc:Canvas'.")
        return value

    def height_field(self, value):
        if not isinstance(value, int):
            self.log_error("height", "height must be int.")
        return value

    def width_field(self, value):
        if not isinstance(value, int):
            self.log_error("width", "width must be int.")
        return value

    def images_field(self, value):
        if isinstance(value, list):
            path = self._path + ("images",)
            return [self._sub_validate(self.AnnotationValidator, i, path,
                                       canvas_uri=self.canvas_uri) for i in value]
        if not value:
            self.log_warning("images", "'images' SHOULD have values.")
            return value
        self.log_error("images", "'images' must be a list.")
        return value

    def other_content_field(self, value):
        if not isinstance(value, list):
            self.log_error("otherContent", "otherContent must be a list.")
            return value
        return [self._uri_type("otherContent", item['@id']) for item in value]