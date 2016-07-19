import urllib.parse
import json
import functools
import contextlib


class ValidatorException:
    """Basic error class with comparison behavior for hashing."""
    def __init__(self, msg, path):
        self.msg = msg
        self.path = path

    def __lt__(self, other):
        return len(self.path) < len(other.path)

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)


class ValidatorWarning(ValidatorException):
    """Class to hold and present warnings."""
    def __str__(self):
        path = ' @ data[%s]' % ']['.join(map(repr, self.path)) if self.path else ''
        output = "Warning: {}".format(self.msg)
        return output + path

    def __repr__(self):
        return "ValidatorWarning('{}', {})".format(self.msg, self.path)


class ValidatorError(ValidatorException):
    """Class to hold and present errors."""
    def __str__(self):
        path = ' @ data[%s]' % ']['.join(map(repr, self.path)) if self.path else ''
        output = "Error: {}".format(self.msg)
        return output + path

    def __repr__(self):
        return "ValidatorError('{}', {})".format(self.msg, self.path)


class LinkedValidatorMixin:
    """Basic support for a linked set of validators with common interfaces."""
    def __init__(self, iiif_validator=None):
        self._errors = set()
        self._warnings = set()
        self.is_valid = None
        self._IIIFValidator = iiif_validator

    @property
    def errors(self):
        return list(self._errors)

    @property
    def warnings(self):
        return list(self._warnings)

    def print_errors(self):
        """Print the errors in a nice format."""
        for err in self._errors:
            print(err)

    def print_warnings(self):
        """Print the warnings in a nice format."""
        for warn in self._warnings:
            print(warn)

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

    def _sub_validate(self, subschema, value, path, **kwargs):
        """Validate a field using another Validator.

        :param subschema: A BaseValidatorMixin implementing object.
        :param value (dict): The data to be validated.
        :param path (tuple): The path where the above data exists.
            Example: ('sequences', 'canvases') for the CanvasValidator.
        :param kwargs: Any keys to subschema._run_validation()
            - canvas_uri: String passed to AnnotationValidator from
              CanvasValidator to ensure 'on' key is valid.
            - raise_warnings: bool to decide if warnings will be recorded
              or not.
        """
        subschema._validate(value, path, **kwargs)
        if subschema._errors:
            self._errors = self._errors | subschema._errors
        if subschema._warnings:
            self._warnings = self._warnings | subschema._warnings
        if subschema.corrected_doc:
            return subschema.corrected_doc
        else:
            return subschema._json


class BaseValidatorMixin(LinkedValidatorMixin):
    """Defines basic validation behaviour and expected attributes
    of any IIIF validators that inherit from it."""

    """The following constants will be iterated through and have their
    values checked on every validation to produce warnings and errors
    based on key constraints. Each inheritor should define these."""
    KNOWN_FIELDS = {}
    FORBIDDEN_FIELDS = {}
    REQUIRED_FIELDS = {}
    RECOMMENDED_FIELDS = {}
    VIEW_HINTS = {}
    VIEW_DIRS = {}
    COMMON_FIELDS = {
        "label", "metadata", "description", "thumbnail", "attribution", "license", "logo",
        "@id", "@type", "viewingHint", "seeAlso", "service", "related", "rendering", "within"
    }

    def __init__(self, iiif_validator=None):
        """You should NOT override ___init___. Override setup() instead."""
        super().__init__(iiif_validator=iiif_validator)
        self._raise_warnings = True
        self._raise_errors = True
        self._path = tuple()
        self._json = None
        self.corrected_doc = None
        self._LangValPairs = None

        self._LangValPairs = {
                '@language': functools.partial(self._repeatable_string_type, "@language"),
                '@value': functools.partial(self._repeatable_string_type, "@value")
            }

        self._MetadataItemSchema = {
                'label': functools.partial(self._str_or_val_lang_type, "label"),
                'value': functools.partial(self._str_or_val_lang_type, "value")
            }

    @staticmethod
    def errors_to_warnings(fn):
        """Cast any errors to warnings on any *_field or *_type function."""
        def coerce_errors(*args, **kwargs):
            self = args[0]
            old_errors = set(self.errors)
            val = fn(*args, **kwargs)
            new_errors = set(self.errors)
            diff = new_errors - old_errors
            for err in diff:
                self._log_warning(err.path[-1], "(error coerced to warning) {}".format(err.msg))
            self._errors = old_errors
            return val
        return coerce_errors

    @staticmethod
    def warnings_to_errors(fn):
        """Cast any warnings to errors on any *_field or *_type function"""
        def coerce_warnings(*args, **kwargs):
            self = args[0]
            old_warnings = set(self.warnings)
            val = fn(*args, **kwargs)
            new_warnings = set(self.warnings)
            diff = new_warnings - old_warnings
            for err in diff:
                self._log_error(err.path[-1], "(warning coerced to error) {}".format(err.msg))
            self._warnings = old_warnings
            return val
        return coerce_warnings

    @contextlib.contextmanager
    def _temp_path(self, path):
        """Temporarily set the path to the given path.

        Useful when validating an embedded dictionary
        and adding its path to the current path.

        :param path (iter): The path to temporarily use.
        """
        old_path = self._path
        try:
            self._path = path
            yield
        finally:
            self._path = old_path

    def _catch_errors(self, fn, *args, **kwargs):
        """Run given function and catch any of the errors it logged.

        The self._errors key will not be changed by using this function."""
        errors = set(self._errors)
        val = fn(*args, **kwargs)
        diff = self._errors - errors
        self._errors = errors
        return val, diff

    def _reset(self, path):
        """Reset the validator to handle a new chunk of data."""
        self._json = None
        self.is_valid = None
        self._errors = set()
        self._path = path

    def _validate(self, json_dict, path=None, raise_warnings=None, **kwargs):
        """Entry point for callers to validate a chunk of data."""
        if raise_warnings is not None:
            self._raise_warnings = raise_warnings

        # Reset the validator object constants.
        if not path:
            path = tuple()
        self._reset(path)

        # Load the json_dict argument as json if a raw string was provided.
        if isinstance(json_dict, str):
            json_dict = json.loads(json_dict)

        self._json = json_dict
        val = self._run_validation(**kwargs)
        val = self._check_common_fields(val)
        self._raise_additional_warnings(val)
        self.corrected_doc = self.modify_final_return(val)

        if self._errors:
            self.is_valid = False
        else:
            self.is_valid = True

    def _compare_dicts(self, schema, value):
        """Compare a schema to a dict.

        Emulates the behaviors of the voluptuous library, which was
        previously used. Iterates through the schema (keys), calling each
        function (values) on the corresponding entry in the `value` dict.

        :param schema: A dict where each key maps to a function.
        :param value: A dict to validate against the schema."""
        corrected = {}
        for k, v in value.items():
            if k in schema:
                corrected[k] = schema[k](v)
            else:
                corrected[k] = v
        return corrected

    def _run_validation(self, **kwargs):
        """Do the actual action of validation. Called by validate()."""
        raise NotImplemented

    def _raise_additional_warnings(self, validation_results):
        """Inspect the block and raise any SHOULD warnings.

        This method is called only if the manifest validates without errors.
        It is passed the block that was just validated. This is the opportunity
        to inspect for fields which SHOULD be there and throw warnings.
        """
        pass

    def modify_final_return(self, validation_results):
        """Do any final corrections or checks on a block before it is returned.

        This method is passed whatever value the validator is about to return to
        it's caller. Here you can check for missing keys, compare neighbours,
        make modifications or additions: anything you'd like to check or correct
        before return.

        :param validation_results: A dict representing a json object.
        :return (dict): The sole argument, with some modification applied to it.
        """
        return validation_results

    def log_warning(self, field, msg):
        """Add a warning to the validator if warnings are being caught.

        :param field: The field the warning was raised on.
        :param msg: The message to associate with the warning.
        """
        if self._raise_warnings:
            self._warnings.add(ValidatorWarning(msg, self._path + (field,)))

    def log_error(self, field, msg):
        """Add an error to the validator.

        :param field: The field the error was raised on.
        :param msg: The message to associate with the error.
        """
        if self._raise_errors:
            self._errors.add(ValidatorError(msg, self._path + (field,)))

    def _check_common_fields(self, val):
        """Validate fields that could appear on any resource."""
        common_fields = {
                "label": self.label_field,
                "metadata": self.metadata_field,
                "description:": self.description_field,
                "thumbnail": self.thumbnail_field,
                "logo": self.logo_field,
                "attribution": self.attribution_field,
                "@type": self.type_field,
                "license": self.license_field,
                "related": self.related_field,
                "rendering": self.rendering_field,
                "service": self.service_field,
                "seeAlso": self.seeAlso_field,
                "within": self.within_field,
        }
        return self._compare_dicts(common_fields, val)

    def _check_recommended_fields(self, resource, r_dict, fields):
        """Log warnings if fields which should be in r_dict are not.

        :param resource (str): The name of the resource represented by r_dict
        :param r_dict (dict): The dict that will have it's keys checked.
        :param fields (list): The keys to check for in r_dict.
        """
        for f in fields:
            if not r_dict.get(f):
                self.log_warning(f, "{} SHOULD have {} field.".format(resource, f))

    def _check_unknown_fields(self, resource, r_dict, fields):
        """Log warnings if any fields which are not known in context are present.

        :param resource (str): The name of the resource represented by r_dict
        :param r_dict (dict): The dict to have its keys checked.
        :param fields (set): Known key names for this resource.
        """
        for key in r_dict.keys():
            if key not in fields:
                self.log_warning(key, "Unknown key '{}' in '{}'".format(key, resource))

    def _check_forbidden_fields(self, resource, r_dict, fields):
        """Log warnings if keys which are forbidden in context are present.

        :param resource (str): The name of the resource represented by r_dict.
        :param r_dict (dict): The dict to have its keys checked.
        :param fields (set): Forbidden key names for this resource.
        """
        for key in r_dict.keys():
            if key in fields:
                self.log_error(key, "Key '{}' is not allowed in '{}'".format(key, resource))

    def _check_required_fields(self, resource, r_dict, fields):
        """Log errors if the required fields are missing.

        :param resource (str): The name of the resource represented by r_dict.
        :param r_dict (dict): The dict to have its keys checked.
        :param fields (set): Forbidden key names for this resource.
        """
        for f in fields:
            if f not in r_dict:
                self.log_error(f, "Key '{}' is required in '{}'".format(f, resource))

    def _check_all_key_constraints(self, resource, r_dict):
        """Call all key constraint checking methods."""
        self._check_common_fields(r_dict)
        self._check_recommended_fields(resource, r_dict, self.RECOMMENDED_FIELDS)
        self._check_unknown_fields(resource, r_dict, self.KNOWN_FIELDS)
        self._check_forbidden_fields(resource, r_dict, self.FORBIDDEN_FIELDS)
        self._check_required_fields(resource, r_dict, self.REQUIRED_FIELDS)

    # Field definitions #
    def _optional(self, field, fn):
        """Wrap a function to make its value optional (null and '' allows)"""
        def new_fn(*args):
            if args[0] == "" or args[0] is None:
                self.log_warning(field, "'{}' field should not be included if it is empty.".format(field))
                return args[0]
            return fn(*args)
        return new_fn

    def _not_allowed(self, field, value):
        """Raise invalid as this key is not allowed in the context."""
        self.log_error(field, "'{}' is not allowed here".format(field))
        return value

    def _str_or_val_lang_type(self, field, value):
        """Check value is str or lang/val pairs, else raise ValidatorError.

        Allows for repeated strings as per 5.3.2.
        """
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            return [self._str_or_val_lang_type(field, val) for val in value]
        if isinstance(value, dict):
            if "@value" not in value:
                self.log_error(field, "Field has no '@value' key where one is required.")
                return value
            if "@language" not in value:
                self.log_error(field, "Field has no '@language' key where one is required.")
                return value
            return self._compare_dicts(self._LangValPairs, value)
        self.log_error(field, "Illegal type (should be str, list, or dict)")
        return value

    def _repeatable_string_type(self, field, value):
        """Allows for repeated strings as per 5.3.2."""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            for val in value:
                if not isinstance(val, str):
                    self.log_error(field, "Overly nested strings: '{}'".format(value))
            return value
        self.log_error(field, "Got '{}' when expecting string or repeated string.".format(value))
        return value

    def _repeatable_uri_type(self, field, value):
        """Allow single or repeating URIs.

        Based on 5.3.2 of Presentation API
        """
        if isinstance(value, list):
            return [self._uri_type(field, val) for val in value]
        else:
            return self._uri_type(field, value)

    def _http_uri_type(self, field, value):
        """Allow single URI that MUST be http(s)

        Based on 5.3.2 of Presentation API
        """
        return self._uri_type(field, value, http=True)

    def _uri_type(self, field, value, http=False):
        """Check value is URI type or raise ValidatorError.

        Allows for multiple URI representations, as per 5.3.1 of the
        Presentation API.
        """
        if isinstance(value, str):
            return self._string_uri(field, value, http)
        elif isinstance(value, dict):
            emb_uri = value.get('@id')
            if not emb_uri:
                self.log_error(field, "URI not found: '{}'".format(value))
                return value
            value['@id'] = self._string_uri(field, emb_uri, http)
            return value
        else:
            self.log_error(field, "Can't parse URI: {}".format(value))
            return value

    def _string_uri(self, field, value, http=False):
        """Validate that value is a string that can be parsed as URI.

        This is the last stop on the recursive structure for URI checking.
        Should not actually be used in schema.
        """
        # Always raise invalid if the string field is not a string.
        if not isinstance(value, str):
            self.log_error(field, "URI is not string: '{}'".format(value))
            return value
        # Try to parse the url.
        try:
            pieces = urllib.parse.urlparse(value)
        except AttributeError as a:
            self.log_error(field, "URI is not valid: '{}'".format(value))
            return value
        if not all([pieces.scheme, pieces.netloc]):
            self.log_error(field, "URI is not valid: '{}'".format(value))
        if http and pieces.scheme not in ['http', 'https']:
            self.log_error(field, "URI must be http: '{}'".format(value))
        return value

    # Common field definitions.
    def id_field(self, value):
        """Validate the `@id` field of the resource."""
        return self._http_uri_type("@id", value)

    def type_field(self, value):
        """Validate the `@type` field of the resource."""
        raise NotImplemented

    def label_field(self, value):
        """Validate the `label` field of the resource."""
        return self._str_or_val_lang_type("label", value)

    def description_field(self, value):
        """Validate the `description` field of the resource."""
        return self._str_or_val_lang_type("description", value)

    def attribution_field(self, value):
        """Validate the `attribution` field of the resource."""
        return self._str_or_val_lang_type("attribution", value)

    def license_field(self, value):
        """Validate the `license` field of the resource."""
        return self._repeatable_uri_type("license", value)

    def related_field(self, value):
        """Validate the `related` field of the resource."""
        return self._repeatable_uri_type("related", value)

    def rendering_field(self, value):
        """Validate the `rendering` field of the resource."""
        return self._repeatable_uri_type("rendering", value)

    def service_field(self, value):
        """Validate the `service` field of the resource."""
        return self._repeatable_uri_type("service", value)

    def seeAlso_field(self, value):
        """Validate the `seeAlso` field of the resource."""
        return self._repeatable_uri_type("seeAlso", value)

    def within_field(self, value):
        """Validate the `within` field of the resource."""
        return self._repeatable_uri_type("within", value)

    def metadata_field(self, value):
        """Validate the `metadata` field of the resource.

        Recurse into keys/values and checks that they are properly formatted.
        """
        if isinstance(value, list):
            with self._temp_path(self._path + ("metadata",)):
                for m in value:
                    if isinstance(m, dict):
                        if "label" not in m:
                            self.log_error("label", "metadata entries must have labels.")
                        elif "value" not in m:
                            self.log_error("value", "metadata entries must have values")
                        else:
                            self._str_or_val_lang_type("value", m.get("value"))
                            self._str_or_val_lang_type("label", m.get("label"))
                    else:
                        self.log_error("value", "Entries must be dictionaries.")
            return value
        self.log_error("metadata", "Metadata MUST be a list")
        return value

    def thumbnail_field(self, value):
        """Validate the `thumbnail` field of the resource."""
        return self._general_image_resource("thumbnail", value)

    def logo_field(self, value):
        """Validate the `logo` field of the resource."""
        return self._general_image_resource("logo", value)

    def _general_image_resource(self, field, value):
        """Image resource validator. Basic logic is:

        -Check if field is string. If yes, warn that IIIF image service is preferred.
        -If it's a IIIF resource, try to validate it.
        -Otherwise, check that it's ID is at least a uri.
        """

        if isinstance(value, str):
            self.log_warning(field, "{} SHOULD be IIIF image service.".format(field))
            return self._uri_type(field, value)
        if isinstance(value, dict):
            path = self._path + (field,)
            service = value.get("service")
            if service and service.get("@context") == "http://iiif.io/api/image/2/context.json":
                return self._sub_validate(self.ImageResourceValidator, service, path,
                                          only_resource=True, raise_warnings=self._raise_warnings)
            else:
                val = self._uri_type(field, value)
                self.log_warning(field, "{} SHOULD be IIIF image service.".format(field))
                return val
        self.log_error(field, "{} type should be string or dict.".format(field))
        return value

    def viewing_hint_field(self, value):
        if value not in self.VIEW_HINTS:
            val, errors = self._catch_errors(self._uri_type, "viewingHint", value)
            if errors:
                self.log_error("viewingHint", "viewingHint '{}' is not valid and not uri.".format(value))
        return value

    def viewing_dir_field(self, value):
        """Validate against VIEW_DIRS list."""
        if value not in self.VIEW_DIRS:
            raise self.log_error("viewingDirection", "viewingDirection '{}' is not valid and not uri.".format(value))
        return value


class IIIFValidator(LinkedValidatorMixin):

    def __init__(self):
        super().__init__(iiif_validator=self)
        self._ManifestValidator = None
        self._ImageResourceValidator = None
        self._CanvasValidator = None
        self._SequenceValidator = None
        self._setup_to_validate()

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
            "sc:Manifest": self._ManifestValidator,
            "sc:Sequence": self._SequenceValidator,
            "sc:Canvas": self._CanvasValidator,
            "oa:Annotation": self._ImageResourceValidator
        }

    def _set_from_sub(self, sub):
        """Set the validation attributes to those of a sub_validator.

        Called after sub_validate'ing with validator sub.

        :param sub: A BaseValidatorMixin implementing Validator.
        """
        self.is_valid = sub.is_valid
        self.corrected_doc = sub.corrected_doc

    def validate(self, json_dict, **kwargs):
        """Determine the correct validator and validate a resource.

        :param json_dict: A dict or str of a json resource.
        """
        self._setup_to_validate()
        if isinstance(json_dict, str):
            try:
                json_dict = json.loads(json_dict)
            except ValueError:
                self._errors.add(ValidatorError("Could not parse json.", tuple()))
                self.is_valid = False

        doc_type = json_dict.get("@type")
        validator = self._TYPE_MAP.get(doc_type)
        if not validator:
            self._errors.add(ValidatorError("Unknown @type: '{}'".format(doc_type), tuple()))
            self.is_valid = False

        self._sub_validate(validator, json_dict, path=None, **kwargs)
        self._set_from_sub(validator)


class ManifestValidator(BaseValidatorMixin):
    PRESENTATION_API_URI = "http://iiif.io/api/presentation/2/context.json"
    IMAGE_API_1 = "http://library.stanford.edu/iiif/image-api/1.1/context.json"
    IMAGE_API_2 = "http://iiif.io/api/image/2/context.json"

    VIEW_DIRS = ['left-to-right', 'right-to-left',
                 'top-to-bottom', 'bottom-to-top']
    VIEW_HINTS = ['individuals', 'paged', 'continuous']

    KNOWN_FIELDS = BaseValidatorMixin.COMMON_FIELDS | {"viewingDirection", "navDate", "sequences", "structures", "@context"}
    FORBIDDEN_FIELDS = {"format", "height", "width", "startCanvas", "first", "last", "total", "next", "prev",
                        "startIndex", "collections", "manifests", "members", "canvases", "resources", "otherContent",
                        "images", "ranges"}
    REQUIRED_FIELDS = {"label", "@context", "@id", "@type", "sequences"}
    RECOMMENDED_FIELDS = {"metadata", "description", "thumbnail"}

    def __init__(self, iiif_validator):
        super().__init__(iiif_validator)
        self.ManifestSchema = {
            '@context': self.context_field,
            'sequences': self.sequences_field,
            'structures': self.structures_field
        }

    def _run_validation(self, **kwargs):
        self._check_all_key_constraints("manifest", self._json)
        return self._compare_dicts(self.ManifestSchema, self._json)

    def type_field(self, value):
        if not value == 'sc:Manifest':
            self.log_error("@type", "@type must be 'sc:Manifest'.")
        return value

    def context_field(self, value):
        if isinstance(value, str):
            if not value == self.PRESENTATION_API_URI:
                self.log_error("@context", "'@context' must be set to '{}'".format(self.PRESENTATION_API_URI))
        if isinstance(value, list):
            if self.PRESENTATION_API_URI not in value:
                self.log_error("@context", "'@context' must be set to '{}'".format(self.PRESENTATION_API_URI))
        return value

    def structures_field(self, value):
        return value

    def sequences_field(self, value):
        """Validate sequence list for Manifest.

        Checks that exactly 1 sequence is embedded.
        """
        path = self._path + ("sequences",)
        if not isinstance(value, list):
            self.log_error("sequences", "'sequences' MUST be a list")
            return value
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
        self.EmbSequenceSchema = {
                '@type': self.type_field,
                '@id': self.id_field,
                'startCanvas': self.startCanvas_field,
                'canvases': self.canvases_field,
                'viewingDirection': self.viewing_dir_field,
                'viewingHint': self.viewing_hint_field,

                '@context': self._not_allowed
            }
        self.LinkedSequenceSchema = {
                '@type': self.type_field,
                '@id': self.id_field,
                'canvases': self._not_allowed
            }

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
        return [self._sub_validate(self.CanvasValidator, c, path,
                                   raise_warnings=self._raise_warnings) for c in value]


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
        self.CanvasSchema = {
                '@id': self.id_field,
                '@type': self.type_field,
                'label': self.label_field,
                'height': self.height_field,
                'width': self.width_field,
                'viewingHint': self.viewing_hint_field,
                'images': self.images_field,
                'other_content': self.other_content_field
            }

    def _run_validation(self, **kwargs):
        self.canvas_uri = self._json['@id']
        self._check_all_key_constraints("Canvas", self._json)
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
            return [self._sub_validate(self.ImageResourceValidator, i, path,
                                       canvas_uri=self.canvas_uri,
                                       raise_warnings=self._raise_warnings) for i in value]
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


class ImageResourceValidator(BaseValidatorMixin):

    KNOWN_FIELDS = BaseValidatorMixin.COMMON_FIELDS | {"motivation", "resource", "on"}
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
