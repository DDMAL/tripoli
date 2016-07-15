import urllib.parse
import json
from voluptuous import Schema, Required, Invalid, MultipleInvalid, ALLOW_EXTRA


class ValidatorWarning:
    """Warning that can hold an in-document path and a message."""
    def __init__(self, msg, path):
        self.msg = msg
        self.path = path

    def __str__(self):
        path = ' @ data[%s]' % ']['.join(map(repr, self.path)) if self.path else ''
        output = "Warning: {}".format(self.msg)
        return output + path

    def __repr__(self):
        return "ValidatorWarning('{}', {})".format(self.msg, self.path)

    def __lt__(self, other):
        return len(self.path) < len(other.path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)


class ValidatorError(Invalid):
    """Subclass of Invalid with preferred behaviour to throw to voluptuous."""

    def __str__(self):
        path = ' @ data[%s]' % ']['.join(map(repr, self.path)) if self.path else ''
        output = "Error: {}".format(self.msg)
        return output + path

    def __repr__(self):
        return "ValidatorError('{}', {})".format(self.msg, self.path)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def __lt__(self, other):
        return len(self.path) < len(other.path)


class BaseValidatorMixin:
    COMMON_FIELDS = {
        "label", "metadata", "description", "thumbnail", "attribution", "license", "logo",
        "@id", "@type", "viewingHint", "seeAlso", "service", "related", "rendering", "within"
    }

    def __init__(self, iiif_validator=None):
        """You should NOT override ___init___. Override setup() instead."""
        self._raise_warnings = True
        self._errors = set()
        self._path = tuple()
        self.is_valid = None
        self._json = None
        self.corrected_doc = None
        self._IIIFValidator = iiif_validator
        self._LangValPairs = None

        self._LangValPairs = Schema(
            {
                Required('@language'): self._repeatable_string_type,
                Required('@value'): self._repeatable_string_type
            }
        )

        self._MetadataItemSchema = Schema(
            {
                'label': self._str_or_val_lang_type,
                'value': self._str_or_val_lang_type
            }
        )

    @property
    def errors(self):
        errs = filter(lambda err: isinstance(err, ValidatorError), self._errors)
        return sorted(errs)

    @property
    def warnings(self):
        warns = filter(lambda warn: isinstance(warn, ValidatorWarning), self._errors)
        return sorted(warns)

    @property
    def ManifestValidator(self):
        return self._IIIFValidator._ManifestValidator

    @property
    def SequenceValidator(self):
        return self._IIIFValidator._SequenceValidator

    @property
    def CanvasValidator(self):
        return self._IIIFValidator._CanvasValidator

    @property
    def ImageResourceValidator(self):
        return self._IIIFValidator._ImageResourceValidator

    @ManifestValidator.setter
    def ManifestValidator(self, value):
        self._IIIFValidator._ManifestValidator = value(self._IIIFValidator)

    @SequenceValidator.setter
    def SequenceValidator(self, value):
        self._IIIFValidator._SequenceValidator = value(self._IIIFValidator)

    @CanvasValidator.setter
    def CanvasValidator(self, value):
        self._IIIFValidator._CanvasValidator = value(self._IIIFValidator)

    @ImageResourceValidator.setter
    def ImageResourceValidator(self, value):
        self._IIIFValidator._ImageResourceValidator = value(self._IIIFValidator)

    @staticmethod
    def errors_to_warnings(fn):
        """Cast any errors to warnings on any *_field or *_type function."""
        def coerce_errors(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except MultipleInvalid as e:
                self = args[0]
                value = args[1]
                for err in e.errors:
                    self._handle_warning(err.path[0],  "Error coerced to warning: '{}'".format(err.msg))
                return value
        return coerce_errors

    @staticmethod
    def warnings_to_errors(fn):
        """Cast any warnings to errors on any *_field or *_type function"""
        def coerce_warnings(*args, **kwargs):
            self = args[0]
            pre_warnings = set(self.warnings)
            val = fn(*args, **kwargs)
            post_warnings = set(self.warnings)
            diff = post_warnings - pre_warnings
            if diff:
                mv = MultipleInvalid()
                for warn in diff:
                    ve = ValidatorError(warn.msg, [warn.path[-1]])
                    mv.add(ve)
                raise mv
            return val
        return coerce_warnings

    def print_errors(self):
        """Print the errors in a nice format."""
        for err in self.errors:
            print(err)

    def print_warnings(self):
        """Print the warnings in a nice format."""
        for warn in self.warnings:
            print(warn)

    def _reset(self, path):
        """Reset the validator to handle a new chunk of data."""
        self._json = None
        self.is_valid = None
        self._errors = set()
        self._path = path

    def _validate(self, json_dict, path=None, raise_warnings=None, **kwargs):
        """Public method to run validation."""
        if raise_warnings is not None:
            self._raise_warnings = raise_warnings

        # Reset the validator object constants.
        if not path:
            path = tuple()
        self._reset(path)

        # Load the json_dict argument as json if a raw string was provided.
        if isinstance(json_dict, str):
            json_dict = json.loads(json_dict)

        try:
            self._json = json_dict
            val = self._run_validation(**kwargs)
            val = self._check_common_fields(val, path)
            self._raise_additional_warnings(val)
            self.corrected_doc = self.modify_validation_return(val)
            self.is_valid = True
        except MultipleInvalid as e:
            # Cast all errors to comparable ones before returning.
            for err in e.errors:
                if isinstance(err, ValidatorWarning):
                    self._errors.add(err)
                elif isinstance(err, ValidatorError):
                    err.path = self._path + tuple(err.path)
                    self._errors.add(err)
                else:
                    err.path = self._path + tuple(err.path)
                    new_err = ValidatorError(err.msg, tuple(err.path))
                    self._errors.add(new_err)
        if self.errors:
            self.is_valid = False

    def _run_validation(self, **kwargs):
        """Do the actual action of validation. Called by validate()."""
        raise NotImplemented

    def _raise_additional_warnings(self, validation_results):
        """Inspect the block and raise any SHOULD warnings.

        This method is called only if the manifest validates without errors.
        It is passed the block that was just validated. This is the opportunity
        to inspect for fields which SHOULD be there and throw warnings.
        """
        raise NotImplemented

    def modify_validation_return(self, validation_results):
        """Do any final corrections or checks on a block before it is returned.

        This method is passed whatever value the validator is about to return to
        it's caller. Here you can check for missing keys, compare neighbours,
        make modifications or additions: anything you'd like to check or correct
        before return.

        :param validation_results: A dict representing a json object.
        :return (dict): The sole argument, with some modification applied to it.
        """
        return validation_results

    def _handle_warning(self, field, msg):
        """Add a warning to the validator if warnings are being caught.

        :param field: The field the warning was raised on.
        :param msg: The message to associate with the warning.
        """
        if self._raise_warnings:
            self._errors.add(ValidatorWarning(msg, self._path + (field,)))

    def _sub_validate(self, subschema, value, path, **kwargs):
        """Validate a field using another Validator.

        :param subschema: A BaseValidatorMixin implementing object.
        :param value (dict): The data to be validated.
        :param path (tuple): The path where the above data exists.
            Example: ('sequences', 'canvases') for the CanvasValidator.
        :param kwargs: Any keys to subschema._run_validation()
            - canvas_uri: String passed to ImageResourceValidator from
              CanvasValidator to ensure 'on' key is valid.
            - raise_warnings: bool to decide if warnings will be recorded
              or not.
        """
        subschema._validate(value, path, **kwargs)
        if subschema._errors:
            self._errors = self._errors | subschema._errors
        if subschema.corrected_doc:
            return subschema.corrected_doc
        else:
            return subschema._json

    def _check_common_fields(self, val, path):
        """Validate fields that could appear on any resource."""
        common_fields = Schema(
            {
                "label": self._label_field,
                "metadata": self._metadata_field,
                "description:": self._description_field,
                "thumbnail": self._thumbnail_field,
                "logo": self._logo_field,
                "attribution": self._attribution_field,
                "@type": self._type_field,
                "license": self._license_field,
                "related": self._related_field,
                "rendering": self._rendering_field,
                "service": self._service_field,
                "seeAlso": self._seeAlso_field,
                "within": self._within_field,
            }, extra=ALLOW_EXTRA
        )
        return common_fields(val)

    def _check_should_warnings(self, resource, r_dict, fields):
        """Raise warnings if fields which should be in r_dict are not.

        :param resource (str): The name of the resource represented by r_dict
        :param r_dict (dict): The dict that will have it's keys checked.
        :param fields (list): The keys to check for in r_dict.
        """
        for f in fields:
            if not r_dict.get(f):
                self._handle_warning(f, "{} SHOULD have {} field.".format(resource, f))

    def _check_unknown_fields(self, resource, r_dict, fields):
        """Raise warnings if any fields which are not known in context are present.

        :param resource (str): The name of the resource represented by r_dict
        :param r_dict (dict): The dict to have its keys checked.
        :param fields (set): Known key names for this resource.
        """
        for key in r_dict.keys():
            if key not in fields:
                self._handle_warning(key, "Unknown key '{}' in '{}'".format(key, resource))

    def _check_forbidden_fields(self, resource, r_dict, fields):
        """Raise warnings if keys which are forbidden in context are present.

        :param resource (str): The name of the resource represented by r_dict
        :param r_dict (dict): The dict to have its keys checked.
        :param fields (set): Forbidden key names for this resource.
        """
        for key in r_dict.keys():
            if key in fields:
                self._handle_warning(key, "Key '{}' is not allowed in '{}'".format(resource))

    # Field definitions #
    def _optional(self, field, fn):
        """Wrap a function to make its value optional (null and '' allows)"""
        def new_fn(*args):
            if args[0] == "" or args[0] is None:
                self._handle_warning(field, "'{}' field should not be included if it is empty.".format(field))
                return args[0]
            return fn(*args)
        return new_fn

    def _not_allowed(self, value):
        """Raise invalid as this key is not allowed in the context."""
        raise ValidatorError("Key is not allowed here.")

    def _str_or_val_lang_type(self, value):
        """Check value is str or lang/val pairs, else raise ValidatorError.

        Allows for repeated strings as per 5.3.2.
        """
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return [self._str_or_val_lang_type(val) for val in value]
        if isinstance(value, dict):
            return self._LangValPairs(value)
        raise ValidatorError("Str_or_val_lang: {}".format(value))

    def _repeatable_string_type(self, value):
        """Allows for repeated strings as per 5.3.2."""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            for val in value:
                if isinstance(val, dict):
                    return self._LangValPairs(val)
                if not isinstance(val, str):
                    raise ValidatorError("Overly nested strings: {}".format(value))
            return value
        raise ValidatorError("repeatable_string: {}".format(value))

    def _repeatable_uri_type(self, value):
        """Allow single or repeating URIs.

        Based on 5.3.2 of Presentation API
        """
        if isinstance(value, list):
            return [self._uri_type(val) for val in value]
        else:
            return self._uri_type(value)

    def _http_uri_type(self, value):
        """Allow single URI that MUST be http(s)

        Based on 5.3.2 of Presentation API
        """
        return self._uri_type(value, http=True)

    def _uri_type(self, value, http=False):
        """Check value is URI type or raise ValidatorError.

        Allows for multiple URI representations, as per 5.3.1 of the
        Presentation API.
        """
        if isinstance(value, str):
            return self._string_uri(value, http)
        elif isinstance(value, dict):
            emb_uri = value.get('@id')
            if not emb_uri:
                raise ValidatorError("URI not found: {} ".format(value))
            return self._string_uri(emb_uri, http)
        else:
            raise ValidatorError("Can't parse URI: {}".format(value))

    def _string_uri(self, value, http=False):
        """Validate that value is a string that can be parsed as URI.

        This is the last stop on the recursive structure for URI checking.
        Should not actually be used in schema.
        """
        # Always raise invalid if the string field is not a string.
        if not isinstance(value, str):
            raise ValidatorError("URI is not String: '{]'".format(value))
        # Try to parse the url.
        try:
            pieces = urllib.parse.urlparse(value)
        except AttributeError as a:
            raise ValidatorError("URI is not valid: '{}'".format(value))
        if not all([pieces.scheme, pieces.netloc]):
            raise ValidatorError("URI is not valid: '{}'".format(value))
        if http and pieces.scheme not in ['http', 'https']:
            raise ValidatorError("URI must be http: '{}'".format(value))
        return value

    # Common field definitions.
    def _id_field(self, value):
        return self._http_uri_type(value)

    def _type_field(self, value):
        raise NotImplemented

    def _label_field(self, value):
        return self._str_or_val_lang_type(value)

    def _description_field(self, value):
        return self._str_or_val_lang_type(value)

    def _attribution_field(self, value):
        return self._str_or_val_lang_type(value)

    def _license_field(self, value):
        return self._repeatable_uri_type(value)

    def _related_field(self, value):
        return self._repeatable_uri_type(value)

    def _rendering_field(self, value):
        return self._repeatable_uri_type(value)

    def _service_field(self, value):
        return self._repeatable_uri_type(value)

    def _seeAlso_field(self, value):
        return self._repeatable_uri_type(value)

    def _within_field(self, value):
        return self._repeatable_uri_type(value)

    def _metadata_field(self, value):
        """General type check for metadata.

        Recurse into keys/values and checks that they are properly formatted.
        """
        if isinstance(value, list):
            return [self._MetadataItemSchema(val) for val in value]
        raise ValidatorError("Metadata key MUST be a list.")

    def _thumbnail_field(self, value):
        """Validate thumbnail field."""
        return self._general_image_resource(value, "thumbnail")

    def _logo_field(self, value):
        """Validate logo field."""
        return self._general_image_resource(value, "logo")

    def _general_image_resource(self, value, field):
        """Image resource validator. Basic logic is:

        -Check if field is string. If yes, warn that IIIF image service is preferred.
        -If it's a IIIF resource, try to validate it.
        -Otherwise, check that it's ID is at least a uri.
        """
        if isinstance(value, str):
            self._handle_warning(field, "{} SHOULD be IIIF image service.".format(field))
            return self._uri_type(value)
        if isinstance(value, dict):
            path = self._path + (field,)
            service = value.get("service")
            if service and service.get("@context") == "http://iiif.io/api/image/2/context.json":
                return self._sub_validate(self.ImageResourceValidator, service, path,
                                          only_resource=True, raise_warnings=self._raise_warnings)
            else:
                val = self._uri_type(value)
                self._handle_warning(field, "{} SHOULD be IIIF image service.".format(field))
                return val


class IIIFValidator(BaseValidatorMixin):
    def __init__(self):
        super().__init__()
        self._IIIFValidator = self
        self._ManifestValidator = None
        self._ImageResourceValidator = None
        self._CanvasValidator = None
        self._SequenceValidator = None

    def _setup_to_validate(self):
        """Make sure all links to sub validators exist."""
        if not self._ManifestValidator:
            self._ManifestValidator = ManifestValidator(self)
        if not self._ImageResourceValidator:
            self._ImageResourceValidator = ImageResourceValidator(self)
        if not self._CanvasValidator:
            self._CanvasValidator = CanvasValidator(self)
        if not self._SequenceValidator:
            self._SequenceValidator = SequenceValidator(self)

        self._TYPE_MAP = {
            "sc:Manifest": self.ManifestValidator,
            "sc:Sequence": self.SequenceValidator,
            "sc:Canvas": self.CanvasValidator,
            "oa:Annotation": self.ImageResourceValidator
        }

    def _set_from_sub(self, sub):
        """Set the validation attributes to those of a sub_validator.

        Called after sub_validate'ing with validator sub.

        :param sub: A BaseValidatorMixin implementing Validator.
        """
        self.is_valid = sub.is_valid
        self._errors = sub._errors
        self.corrected_doc = sub.corrected_doc

    def validate(self, json_dict, **kwargs):
        self._setup_to_validate()
        if isinstance(json_dict, str):
            try:
                json_dict = json.loads(json_dict)
            except ValueError:
                self._errors.add(ValidatorError("Could not parse json."))
                self.is_valid = False

        doc_type = json_dict.get("@type")
        validator = self._TYPE_MAP.get(doc_type)
        if not validator:
            self._errors.add(ValidatorError("Unknown @type: '{}'".format(doc_type)))
            self.is_valid = False

        self._sub_validate(validator, json_dict, path=None, **kwargs)
        self._set_from_sub(validator)

    def validate_canvas(self, json_dict, **kwargs):
        self._sub_validate(self.CanvasValidator, json_dict, path=None, **kwargs)


class ManifestValidator(BaseValidatorMixin):
    PRESENTATION_API_URI = "http://iiif.io/api/presentation/2/context.json"
    IMAGE_API_1 = "http://library.stanford.edu/iiif/image-api/1.1/context.json"
    IMAGE_API_2 = "http://iiif.io/api/image/2/context.json"

    VIEW_DIRS = ['left-to-right', 'right-to-left',
                 'top-to-bottom', 'bottom-to-top']
    VIEW_HINTS = ['individuals', 'paged', 'continuous']

    KNOWN_FIELDS = BaseValidatorMixin.COMMON_FIELDS | {"viewingDirection", "navDate", "sequences", "structures"}

    FORBIDDEN_FIELDS = {"format", "height", "width", "startCanvas", "first", "last", "total", "next", "prev",
                        "startIndex", "collections", "manifests", "members", "canvases", "resources", "otherContent",
                        "images", "ranges"}

    REQUIRED_FIELDS = {"label", "@context", "@id", "@type", "sequences"}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.ManifestSchema = Schema({
            Required('label'): self._label_field,
            Required('@context'): self._context_field,

            # Technical properties
            Required('@id'): self._id_field,
            Required('@type'): self._type_field,
            'viewingDirection': self._viewing_dir_field,
            'viewingHint': self._viewing_hint_field,

            Required('sequences'): self._sequences_field
        }, extra=ALLOW_EXTRA)

    def _run_validation(self, **kwargs):
        return self.ManifestSchema(self._json)

    def _raise_additional_warnings(self, validation_results):
        self._check_should_warnings("manifest", validation_results, ["metadata", "description", "thumbnail"])
        self._check_unknown_fields("manifest", validation_results, self.KNOWN_FIELDS)
        self._check_forbidden_fields("manifest", validation_results, self.FORBIDDEN_FIELDS)

    def _type_field(self, value):
        if not value == 'sc:Manifest':
            raise Invalid("@type must be 'sc:Manifest'.")
        return value

    def _context_field(self, value):
        if isinstance(value, str):
            if not value == self.PRESENTATION_API_URI:
                raise ValidatorError("'@context' must be set to '{}'".format(self.PRESENTATION_API_URI))
        if isinstance(value, list):
            if self.PRESENTATION_API_URI not in value:
                raise ValidatorError("'@context' must be set to '{}'".format(self.PRESENTATION_API_URI))
        return value

    def _metadata_field(self, value):
        """General type check for metadata.

        Recurse into keys/values and checks that they are properly formatted.
        """
        if isinstance(value, list):
            return [self._MetadataItemSchema(val) for val in value]
        raise ValidatorError("Metadata key MUST be a list.")

    def _viewing_dir_field(self, value):
        """Validate against VIEW_DIRS list."""
        if value not in self.VIEW_DIRS:
            raise ValidatorError("viewingDirection: {}".format(value))
        return value

    def _viewing_hint_field(self, value):
        """Validate against VIEW_HINTS list."""
        if value not in self.VIEW_HINTS:
            raise ValidatorError("viewingHint: {}".format(value))
        return value

    def _sequences_field(self, value):
        """Validate sequence list for Manifest.

        Checks that exactly 1 sequence is embedded.
        """
        path = self._path + ("sequences",)
        if not isinstance(value, list):
            raise ValidatorError("'sequences' must be a list.")
        lst = [self._sub_validate(self.SequenceValidator, value[0], path,
                                  raise_warnings=self._raise_warnings, emb=True)]
        lst.extend([self._sub_validate(self.SequenceValidator, value[s], path,
                                       raise_warnings=self._raise_warnings, emb=False) for s in lst[1:]])
        return lst


class SequenceValidator(BaseValidatorMixin):
    VIEW_DIRS = {'left-to-right', 'right-to-left',
                 'top-to-bottom', 'bottom-to-top'}
    VIEW_HINTS = {'individuals', 'paged', 'continuous'}

    KNOWN_FIELDS = BaseValidatorMixin.COMMON_FIELDS | {"viewingDirection", "startCanvas", "canvases"}

    FORBIDDEN_FIELDS = {"format", "height", "width", "navDate", "first", "last", "total", "next", "prev",
                        "startIndex", "collections", "manifests", "sequences", "structures", "resources",
                        "otherContent", "images", "ranges"}

    REQUIRED_FIELDS = {"@type", "canvases"}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.EmbSequenceSchema = None
        self.LinkedSequenceSchema = None
        self._setup()

    def _setup(self):

        # An embedded sequence must contain canvases.
        self.EmbSequenceSchema = Schema(
            {
                Required('@type'): self._type_field,
                '@id': self._id_field,
                'startCanvas': self._startCanvas_field,
                Required('canvases'): self._canvases_field,
                'viewingDirection': self._viewing_direction_field,
                'viewingHint': self._viewing_hint_field,

                '@context': self._not_allowed
            },
            extra=ALLOW_EXTRA
        )

        # A linked sequence must have an @id and no canvases
        self.LinkedSequenceSchema = Schema(
            {
                Required('@type'): self._type_field,
                Required('@id'): self._id_field,
                'canvases': self._not_allowed
            },
            extra=ALLOW_EXTRA
        )

    def _run_validation(self, **kwargs):
        return self._validate_sequence(**kwargs)

    def _validate_sequence(self, emb=True):
        value = self._json
        if emb:
            return self.EmbSequenceSchema(value)
        else:
            return self.LinkedSequenceSchema(value)

    def _raise_additional_warnings(self, validation_results):
        pass

    def _type_field(self, value):
        if value != "sc:Sequence":
            raise Invalid("@type must be 'sc:Sequence'.")
        return value

    def _startCanvas_field(self, value):
        return self._uri_type(value)

    def _canvases_field(self, value):
        """Validate canvas list for Sequence."""
        if not isinstance(value, list):
            raise ValidatorError("'canvases' MUST be a list.")
        if len(value) < 1:
            raise ValidatorError("'canvases' MUST have at least one entry.")
        path = self._path + ("canvases",)
        return [self._sub_validate(self.CanvasValidator, c, path,
                                   raise_warnings=self._raise_warnings) for c in value]

    def _viewing_hint_field(self, value):
        if value not in self.VIEW_HINTS:
            try:
                return self._uri_type(value)
            except Invalid:
                raise ValidatorError("Viewing hint is not known and not uri.")
        return value

    def _viewing_direction_field(self, value):
        if value not in self.VIEW_DIRS:
            raise Invalid("Unknown viewingDirection.")
        return value


class CanvasValidator(BaseValidatorMixin):
    VIEW_HINTS = {'non-paged', 'facing-pages'}

    KNOWN_FIELDS = BaseValidatorMixin.COMMON_FIELDS | {"height", "width", "otherContent", "images"}

    FORBIDDEN_FIELDS = {"format", "viewingDirection", "navDate", "startCanvas", "first", "last", "total",
                        "next", "prev", "startIndex", "collections", "manifests", "members", "sequences",
                        "structures", "canvases", "resources", "ranges"}

    REQUIRED_FIELDS = {"label", "@id", "@type", "height", "width"}

    def __init__(self, iiif_validator):
        """You should not override ___init___. Override setup() instead."""
        super().__init__(iiif_validator)
        self.CanvasSchema = None
        self._setup()

    def _setup(self):
        self.CanvasSchema = Schema(
            {
                Required('@id'): self._id_field,
                Required('@type'): self._type_field,
                Required('label'): self._label_field,
                Required('height'): self._height_field,
                Required('width'): self._width_field,
                'viewingHint': self._viewing_hint_field,
                'images': self._images_field,
                'other_content': self._other_content_field
            },
            extra=ALLOW_EXTRA
        )

    def _run_validation(self, **kwargs):
        self.canvas_uri = self._json['@id']
        return self.CanvasSchema(self._json)

    def _raise_additional_warnings(self, validation_results):
        # Canvas should have a thumbnail if it has multiple images.
        if len(validation_results.get('images', [])) > 1 and not validation_results.get("thumbnail"):
            self._handle_warning("thumbnail", "Canvas SHOULD have a thumbnail when there is more than one image")

    def _type_field(self, value):
        if value != "sc:Canvas":
            raise Invalid("@type must be 'sc:Canvas'.")
        return value

    def _height_field(self, value):
        if not isinstance(value, int):
            raise Invalid("height must be int.")

    def _width_field(self, value):
        if not isinstance(value, int):
            raise Invalid("width must be an int.")

    def _images_field(self, value):
        if isinstance(value, list):
            path = self._path + ("images",)
            return [self._sub_validate(self.ImageResourceValidator, i, path,
                                       canvas_uri=self.canvas_uri,
                                       raise_warnings=self._raise_warnings) for i in value]
        if not value:
            return
        raise ValidatorError("'images' must be a list")

    def _other_content_field(self, value):
        if not isinstance(value, list):
            raise ValidatorError("otherContent must be list!")
        return [self._uri_type(item['@id']) for item in value]

    def _viewing_hint_field(self, value):
        if value not in self.VIEW_HINTS:
            try:
                return self._uri_type(value)
            except Invalid:
                raise ValidatorError("Viewing hint is not known and not uri.")


class ImageResourceValidator(BaseValidatorMixin):

    KNOWN_FIELDS = BaseValidatorMixin.COMMON_FIELDS
    FORBIDDEN_FIELDS = {"format", "height", "width", "viewingDirection", "navDate", "startCanvas", "first",
                        "last", "total", "next", "prev", "startIndex", "collections", "manifests", "members",
                        "sequences", "structures", "canvases", "resources", "otherContent", "images", "ranges"}
    REQUIRED_FIELDS = {"@type"}
    
    def __init__(self, iiif_validator):
        """You should not override ___init___. Override setup() instead."""
        super().__init__(iiif_validator)
        self.ImageSchema = None
        self.ImageResourceSchema = None
        self.ServiceSchema = None
        self.canvas_uri = None
        self._setup()

    def _setup(self):
        self.ImageSchema = Schema(
            {
                "@id": self._id_field,
                Required('@type'): self._type_field,
                Required('motivation'): self._motivation_field,
                Required('resource'): self._image_resource_field,
                Required("on"): self._on_field,
                'height': self._height_field,
                'width': self._width_field
            }, extra=ALLOW_EXTRA
        )
        self.ImageResourceSchema = Schema(
            {
                Required('@id'): self._id_field,
                '@type': self._resource_type_field,
                "service": self._resource_image_service_field
            }, extra=ALLOW_EXTRA
        )

        self.ServiceSchema = Schema(
            {
                '@context': self._repeatable_uri_type,
                '@id': self._uri_type,
                'profile': self._service_profile_field,
                'label': str
            }, extra=ALLOW_EXTRA
        )

    def _run_validation(self, canvas_uri=None, only_resource=False, **kwargs):
        self.canvas_uri = canvas_uri
        if only_resource:
            return self.ImageResourceSchema(self._json)
        else:
            return self.ImageSchema(self._json)

    def _raise_additional_warnings(self, validation_results):
        self._check_should_warnings("Annotation", validation_results, ["@id"])

    def _type_field(self, value):
        if value != "oa:Annotation":
            raise Invalid("@type must be 'oa:Annotation'.")
        return value

    def _motivation_field(self, value):
        if value != "sc:painting":
            raise Invalid("motivation must be 'sc:painting'.")
        return value

    def _height_field(self, value):
        if not isinstance(value, int):
            raise Invalid("height must be int.")

    def _width_field(self, value):
        if not isinstance(value, int):
            raise Invalid("width must be an int.")

    def _on_field(self, value):
        """Validate the 'on' property of an Annotation."""
        if self.canvas_uri and value != self.canvas_uri:
            raise ValidatorError("'on' must reference the canvas URI.")
        return value

    def _resource_type_field(self, value):
        """Validate the '@type' field of an Image Resource."""
        if value != 'dctypes:Image':
            self._handle_warning("@type", "'@type' field SHOULD be 'dctypes:Image'")
        return value

    def _image_resource_field(self, value):
        """Validate image resources inside images list of Canvas"""
        if value.get('@type') == 'oa:Choice':
            return self.ImageResourceSchema(value['default'])
        return self.ImageResourceSchema(value)

    def _resource_image_service_field(self, value):
        """Validate against Service sub-schema."""
        if isinstance(value, str):
            return self._uri_type(value)
        elif isinstance(value, list):
            return [self._resource_image_service_field(val) for val in value]
        else:
            return self.ServiceSchema(value)

    def _service_profile_field(self, value):
        """Profiles in services are a special case.

        The profile key can contain a uri, or a list with extra
        metadata and a uri in the first position.
        """
        if isinstance(value, list):
            return self._uri_type(value[0])
        else:
            return self._uri_type(value)
