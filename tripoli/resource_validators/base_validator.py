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

import contextlib
import functools
import json
import traceback
import urllib.parse
import copy
import uuid

from ..mixins import LinkedValidatorMixin, SubValidationMixin
from ..validator_logging import ValidatorLogError, ValidatorLogWarning
from ..exceptions import FailFastException


class BaseValidator(LinkedValidatorMixin, SubValidationMixin):
    """Defines basic validation behaviour and expected attributes
    of any IIIF validators that inherit from it."""

    PRESENTATION_API_URI = "http://iiif.io/api/presentation/2/context.json"
    IMAGE_API_2 = "http://iiif.io/api/image/2/context.json"
    IMAGE_API_1 = "http://iiif.io/api/image/1/context.json"

    # The following constants will be iterated through and have their
    # values checked on every validation to produce warnings and errors
    # based on key constraints. Each inheritor should define these.

    #: The fields which may appear on this resource.
    KNOWN_FIELDS = {}

    #: The fields which are forbidden on this resource.
    FORBIDDEN_FIELDS = {}

    #: The fields which are required on this resource.
    REQUIRED_FIELDS = {}

    #: The fields which are recommended on this resource.
    RECOMMENDED_FIELDS = {}

    # The set of acceptable viewHints on this resource.
    VIEW_HINTS = {}

    # The set of acceptable viewDirections on this resource.
    VIEW_DIRS = {}

    # The set of fields which may appear on _any_ resource.
    COMMON_FIELDS = {
        "label", "metadata", "description", "thumbnail", "attribution", "license", "logo",
        "@id", "@type", "viewingHint", "seeAlso", "service", "related", "rendering", "within"
    }

    def __init__(self, iiif_validator=None):
        LinkedValidatorMixin.__init__(self, iiif_validator=iiif_validator)
        SubValidationMixin.__init__(self)
        self._path = tuple()
        self._json = None
        self.corrected_doc = None

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
        """Cast any errors to warnings on any ``*_field`` or ``*_type`` function."""

        def coerce_errors(*args, **kwargs):
            self = args[0]
            old_errors = set(self.errors)
            old_fail_fast = self.fail_fast
            try:
                self._IIIFValidator.fail_fast = False
                val = fn(*args, **kwargs)
            finally:
                self._IIIFValidator.fail_fast = old_fail_fast
            new_errors = set(self.errors)
            diff = new_errors - old_errors
            for err in diff:
                self.log_warning(err.path[-1], "(error coerced to warning) {}".format(err.msg))
            self._errors = old_errors
            return val

        return coerce_errors

    @staticmethod
    def warnings_to_errors(fn):
        """Cast any warnings to errors on any ``*_field`` or ``*_type`` function."""

        def coerce_warnings(*args, **kwargs):
            self = args[0]
            old_warnings = set(self.warnings)
            val = fn(*args, **kwargs)
            new_warnings = set(self.warnings)
            diff = new_warnings - old_warnings
            for err in diff:
                self.log_error(err.path[-1], "(warning coerced to error) {}".format(err.msg))
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

    def mute_errors(self, fn, *args, **kwargs):
        """Run given function and catch any of the errors it logged.

        The self._errors key will not be changed by using this function.

        The fail_fast option is temporarily set to false while the function
        is run.
        """
        errors = set(self._errors)
        old_fail_fast = self.fail_fast
        try:
            self._IIIFValidator.fail_fast = False
            val = fn(*args, **kwargs)
        finally:
            self._IIIFValidator.fail_fast = old_fail_fast
        diff = self._errors - errors
        self._errors = errors
        return val, diff

    def _reset(self, path):
        """Reset the validator to handle a new chunk of data."""
        self._json = None
        self.is_valid = None
        self._errors = set()
        self._warnings = set()
        self._path = path

    def setup(self):
        pass

    def _validate(self, json_dict, path=None, **kwargs):
        """Entry point for callers to validate a chunk of data."""

        # Reset the validator object constants.
        if not path:
            path = tuple()
        self._reset(path)

        # Load the json_dict argument as json if a raw string was provided.
        if isinstance(json_dict, str):
            json_dict = json.loads(json_dict)

        self._json = json_dict
        try:
            val = self._run_validation(**kwargs)
            val = self._check_common_fields(val)
            self._raise_additional_warnings(val)
            self.corrected_doc = self.modify_final_return(val)
        finally:
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
        corrected = copy.copy(value)
        for key, fn in schema.items():
            if key in value:
                corrected[key] = fn(corrected[key])
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
        if self.collect_warnings:
            tb = traceback.extract_stack()[:-1] if self.debug else None
            self._warnings.add(ValidatorLogWarning(msg, self._path + (field,), tb))

    def log_error(self, field, msg):
        """Add an error to the validator.

        :param field: The field the error was raised on.
        :param msg: The message to associate with the error.
        """
        if self.collect_errors:
            tb = traceback.extract_stack()[:-1] if self.debug else None
            self._errors.add(ValidatorLogError(msg, self._path + (field,), tb))
        if self.fail_fast:
            raise FailFastException

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
        self._check_forbidden_fields(resource, r_dict, self.FORBIDDEN_FIELDS)
        self._check_required_fields(resource, r_dict, self.REQUIRED_FIELDS)
        self._check_recommended_fields(resource, r_dict, self.RECOMMENDED_FIELDS)
        self._check_unknown_fields(resource, r_dict, self.KNOWN_FIELDS)
        return self._check_common_fields(r_dict)


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
        """Check value is str or lang/val pairs, else raise ValidatorLogError.

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
        """Check value is URI type or raise ValidatorLogError.

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
        """Validate the ``@id`` field of the resource."""
        if value.startswith("urn:uuid:"):
            id_uuid = value.replace("urn:uuid:", "")
            try:
                uuid.UUID(id_uuid)
            except ValueError:
                self.log_error("@id", "Invalid UUID in @id.")
            finally:
                return value
        return self._http_uri_type("@id", value)

    def type_field(self, value):
        """Validate the ``@type`` field of the resource."""
        raise NotImplemented

    def label_field(self, value):
        """Validate the ``label`` field of the resource."""
        return self._str_or_val_lang_type("label", value)

    def description_field(self, value):
        """Validate the ``description`` field of the resource."""
        return self._str_or_val_lang_type("description", value)

    def attribution_field(self, value):
        """Validate the ``attribution`` field of the resource."""
        return self._str_or_val_lang_type("attribution", value)

    def license_field(self, value):
        """Validate the ``license`` field of the resource."""
        return self._repeatable_uri_type("license", value)

    def related_field(self, value):
        """Validate the ``related`` field of the resource."""
        return self._repeatable_uri_type("related", value)

    def rendering_field(self, value):
        """Validate the ``rendering`` field of the resource."""
        return self._repeatable_uri_type("rendering", value)

    def service_field(self, value):
        """Validate the ``service`` field of the resource."""
        return self._repeatable_uri_type("service", value)

    def seeAlso_field(self, value):
        """Validate the ``seeAlso`` field of the resource."""
        return self._repeatable_uri_type("seeAlso", value)

    def within_field(self, value):
        """Validate the ``within`` field of the resource."""
        return self._repeatable_uri_type("within", value)

    def height_field(self, value):
        """Validate ``height`` field."""
        if not isinstance(value, int):
            self.log_error("height", "height must be int.")
        return value

    def width_field(self, value):
        """Validate ``width`` field."""
        if not isinstance(value, int):
            self.log_error("width", "width must be int.")
        return value

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
        """Validate the ``thumbnail`` field of the resource."""
        return self._general_image_resource("thumbnail", value)

    def logo_field(self, value):
        """Validate the ``logo`` field of the resource."""
        return self._general_image_resource("logo", value)

    def _general_image_resource(self, field, value):
        """Image resource validator for logos and thumbnails. Basic logic is:

        -Check if field is string. If yes, warn that IIIF image service is preferred.
        -If a IIIF image service is avaliable,  try to validate it.
        -Otherwise, check that it's ID is at least a uri.
        """

        if isinstance(value, str):
            self.log_warning(field, "{} SHOULD be IIIF image service.".format(field))
            return self._uri_type(field, value)
        if isinstance(value, dict):
            service = value.get("service")
            if service and service.get("@context") == "http://iiif.io/api/image/2/context.json":
                value['service'] = self.ImageContentValidator.service_field(service)
                return value
            else:
                val = self._uri_type(field, value)
                self.log_warning(field, "{} SHOULD be IIIF image service.".format(field))
                return val
        self.log_error(field, "{} type should be string or dict.".format(field))
        return value

    def viewing_hint_field(self, value):
        """Validate ``viewingHint`` field against ``VIEW_HINTS`` set."""
        if value not in self.VIEW_HINTS:
            val, errors = self.mute_errors(self._uri_type, "viewingHint", value)
            if errors:
                self.log_error("viewingHint", "viewingHint '{}' is not valid and not uri.".format(value))
        return value

    def viewing_dir_field(self, value):
        """Validate ``viewingDir`` field against ``VIEW_DIRS`` set."""
        if value not in self.VIEW_DIRS:
            self.log_error("viewingDirection", "viewingDirection '{}' is not valid and not uri.".format(value))
        return value
