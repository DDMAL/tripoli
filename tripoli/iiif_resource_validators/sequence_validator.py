from collections import OrderedDict

from tripoli.iiif_resource_validators.base_validator import BaseValidator


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
        self.EmbSequenceSchema = OrderedDict((
            ('@type', self.type_field),
            ('@context', self._not_allowed),
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

    def _run_validation(self, **kwargs):
        self._check_all_key_constraints("sequence", self._json)
        return self._validate_sequence(**kwargs)

    def _validate_sequence(self, emb=True):
        if emb:
            return self._compare_dicts(self.EmbSequenceSchema, self._json)
        else:
            return self._compare_dicts(self.LinkedSequenceSchema, self._json)

    def _raise_additional_warnings(self, validation_results):
        pass

    def type_field(self, value):
        if value != "sc:Sequence":
            self.log_error("@type", "@type must be 'sc:Sequence'")
        return value

    def startCanvas_field(self, value):
        return self._uri_type("startCanvas", value)

    def canvases_field(self, value):
        """Validate canvas list for Sequence."""
        if not isinstance(value, list):
            self.log_error("canvases", "'canvases' MUST be a list.")
            return value
        if len(value) < 1:
            self.log_error("canvases", "'canvases' MUST have at least one entry")
            return value
        path = self._path + ("canvases",)
        return [self._sub_validate(self.CanvasValidator, c, path) for c in value]
