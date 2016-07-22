from collections import OrderedDict

from .base_validator import BaseValidator


class AnnotationValidator(BaseValidator):
    KNOWN_FIELDS = BaseValidator.COMMON_FIELDS | {"motivation", "resource", "on"}
    FORBIDDEN_FIELDS = {"format", "height", "width", "viewingDirection", "navDate", "startCanvas", "first",
                        "last", "total", "next", "prev", "startIndex", "collections", "manifests", "members",
                        "sequences", "structures", "canvases", "resources", "otherContent", "images", "ranges"}
    REQUIRED_FIELDS = {"@type", "on", "motivation"}
    RECOMMENDED_FIELDS = {"@id"}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.ImageSchema = OrderedDict((
            ("@id", self.id_field),
            ('@type', self.type_field),
            ('motivation', self.motivation_field),
            ("on", self.on_field),
            ('height', self.height_field),
            ('width', self.width_field),
            ('resource', self.resource_field)
        ))

        self.canvas_uri = None

    def _raise_additional_warnings(self, validation_results):
        pass

    def _run_validation(self, canvas_uri=None, **kwargs):
        self.canvas_uri = canvas_uri
        self._check_all_key_constraints("annotation", self._json)
        return self._compare_dicts(self.ImageSchema, self._json)

    def type_field(self, value):
        """Assert that ``@type == 'oa:Annotation'``."""
        if value != "oa:Annotation":
            self.log_error("@type", "@type must be 'oa:Annotation'.")
        return value

    def motivation_field(self, value):
        """Assert that ``motivation == 'sc:painting'``."""
        if value != "sc:painting":
            self.log_error("motivation", "motivation must be 'sc:painting'.")
        return value

    def on_field(self, value):
        """Validate the ``on`` field."""
        if self.canvas_uri and value != self.canvas_uri:
            self.log_error("on", "'on' must reference the canvas URI.")
        return value

    def resource_field(self, value):
        """Validate ``resources`` list.

        Calls a sub-validation procedure handled by the :class:`ImageContentValidator`.
        """
        path = self._path + ("resource", )
        return self._sub_validate(self.ImageContentValidator, value, path)
