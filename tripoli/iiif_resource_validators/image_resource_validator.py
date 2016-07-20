import functools

from tripoli.iiif_resource_validators.base_validator import BaseValidator


class ImageResourceValidator(BaseValidator):
    KNOWN_FIELDS = BaseValidator.COMMON_FIELDS | {"motivation", "resource", "on"}
    FORBIDDEN_FIELDS = {"format", "height", "width", "viewingDirection", "navDate", "startCanvas", "first",
                        "last", "total", "next", "prev", "startIndex", "collections", "manifests", "members",
                        "sequences", "structures", "canvases", "resources", "otherContent", "images", "ranges"}
    REQUIRED_FIELDS = {"@type", "on", "motivation"}
    RECOMMENDED_FIELDS = {"@id"}

    def __init__(self, iiif_validator):
        """You should not override ___init___. Override setup() instead."""
        super().__init__(iiif_validator)
        self.ImageSchema = {
            "@id": self.id_field,
            '@type': self.type_field,
            'motivation': self.motivation_field,
            'resource': self.image_resource_field,
            "on": self.on_field,
            'height': self.height_field,
            'width': self.width_field
        }
        self.ImageResourceSchema = {
            '@id': self.id_field,
            '@type': self.resource_type_field,
            "service": self.resource_image_service_field
        }
        self.ServiceSchema = {
            '@context': functools.partial(self._repeatable_uri_type, "@context"),
            '@id': self.id_field,
            'profile': self.service_profile_field,
            'label': self.label_field
        }

        self.canvas_uri = None

    def _raise_additional_warnings(self, validation_results):
        pass

    def _run_validation(self, canvas_uri=None, only_resource=False, **kwargs):
        self.canvas_uri = canvas_uri
        if only_resource:
            return self._compare_dicts(self.ImageResourceSchema, self._json)
        else:
            self._check_all_key_constraints("ImageResource", self._json)
            return self._compare_dicts(self.ImageSchema, self._json)

    def type_field(self, value):
        if value != "oa:Annotation":
            self.log_error("@type", "@type must be 'oa:Annotation'.")
        return value

    def motivation_field(self, value):
        if value != "sc:painting":
            self.log_error("motivation", "motivation must be 'sc:painting'.")
        return value

    def height_field(self, value):
        if not isinstance(value, int):
            self.log_error("height", "height must be int.")
        return value

    def width_field(self, value):
        if not isinstance(value, int):
            self.log_error("width", "width must be int.")
        return value

    def on_field(self, value):
        """Validate the 'on' property of an Annotation."""
        if self.canvas_uri and value != self.canvas_uri:
            self.log_error("on", "'on' must reference the canvas URI.")
        return value

    def image_resource_field(self, value):
        """Validate image resources inside images list of Canvas"""
        with self._temp_path(self._path + ("resource",)):
            self._check_required_fields("ImageContent", value, ("@id",))
            if value.get('@type') == 'oa:Choice':
                return self._compare_dicts(self.ImageResourceSchema, value['default'])
            return self._compare_dicts(self.ImageResourceSchema, value)

    def resource_type_field(self, value):
        """Validate the '@type' field of an Image Resource."""
        if value != 'dctypes:Image':
            self.log_warning("@type", "'@type' field SHOULD be 'dctypes:Image'")
        return value

    def resource_image_service_field(self, value):
        """Validate against Service sub-schema."""
        if isinstance(value, str):
            return self._uri_type("service", value)
        elif isinstance(value, list):
            return [self.resource_image_service_field(val) for val in value]
        else:
            with self._temp_path(self._path + ("service",)):
                self._check_required_fields("service", value, ("@context", "@id", "profile"))
                self._check_recommended_fields("service", value, ("@id", "profile"))
                return self._compare_dicts(self.ServiceSchema, value)

    def service_profile_field(self, value):
        """Profiles in services are a special case.

        The profile key can contain a uri, or a list with extra
        metadata and a uri in the first position.
        """
        if isinstance(value, list):
            return self._uri_type("profile", value[0])
        else:
            return self._uri_type("profile", value)
