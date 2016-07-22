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
        path = self._path + ("sequences",)
        if not isinstance(value, list):
            self.log_error("sequences", "'sequences' MUST be a list")
            return value
        lst = [self._sub_validate(self.SequenceValidator, value[0], path, emb=True)]
        lst.extend([self._sub_validate(self.SequenceValidator, value[s], path, emb=False) for s in lst[1:]])
        return lst