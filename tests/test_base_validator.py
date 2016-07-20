import inspect
import unittest

from tripoli import IIIFValidator
from tripoli.iiif_resource_validators.base_validator import BaseValidator


class TestBaseValidatorMixin(unittest.TestCase):

    def setUp(self):
        iv = IIIFValidator()
        iv.fail_fast = False
        self.base_validator = BaseValidator(iv)

    def has_error(self, error):
        """Check if a particular error was raised."""
        return error in self.base_validator._errors

    def has_errors(self):
        return bool(self.base_validator._errors)

    def has_warning(self, warning):
        return warning in self.base_validator._warnings

    def has_warnings(self):
        return bool(self.base_validator._warnings)

    def has_warnings_or_errors(self):
        return not (bool(self.base_validator._warnings) or bool(self.base_validator._errors))

    def clear_errors(self):
        self.base_validator._errors = set()

    def clear_warnings(self):
        self.base_validator._warnings = set()

    def clear_errors_and_warnings(self):
        self.base_validator._errors = set()
        self.base_validator._warnings = set()

    def assert_no_errors_with_inputs(self, fn, inputs):
        """Run validation fn on each input, asserting no error is logged."""
        argc = len(inspect.signature(fn).parameters)
        for arg in inputs:
            val = fn('unknown_field', arg) if argc >= 2 else fn(arg)
            try:
                self.assertFalse(self.has_errors(), "{} is not valid input".format(arg))
                self.assertEqual(arg, val)
            finally:
                self.clear_errors()

    def assert_errors_with_inputs(self, fn, inputs):
        """Run validation fn on each input, asserting each logs an error."""
        argc = len(inspect.signature(fn).parameters)
        for arg in inputs:
            val = fn('unknown_field', arg) if argc >= 2 else fn(arg)
            try:
                self.assertTrue(self.has_errors(), "{} is valid input".format(arg))
                self.assertEqual(arg, val)
            finally:
                self.clear_errors()

    def test_str_or_val_lang_type(self):
        """Allows stings, lists of strings, val/lang dicts, and lists of val/lang dicts"""
        valid_inputs = ['hello', ['hello', 'there'], {'@language': 'en', '@value': 'hello'},
                        [{'@language': 'en', '@value': 'hello'}, {'@language': 'fr', '@value': 'bonjour'}]]
        self.assert_no_errors_with_inputs(self.base_validator._str_or_val_lang_type, valid_inputs)

        invalid_inputs = [0, {'@value': 14, '@language': 'en'}, {'@value': 'Hello'}]
        self.assert_errors_with_inputs(self.base_validator._str_or_val_lang_type, invalid_inputs)

    def test_repeatable_str_type(self):
        """Allows strings or lists of strings."""
        valid_inputs = ['hello', ['hello', 'there']]
        self.assert_no_errors_with_inputs(self.base_validator._repeatable_string_type, valid_inputs)

    def test_repeatable_uri_type(self):
        """Allow a single uri or list of uris (in both uri formats)"""
        valid_inputs = ['http://google.ca', ['http://google.com', {'@id': 'http://bing.com'}]]
        self.assert_no_errors_with_inputs(self.base_validator._repeatable_uri_type, valid_inputs)

        invalid_inputs = ['hello', ['hello', 'everyone']]
        self.assert_errors_with_inputs(self.base_validator._repeatable_uri_type, invalid_inputs)

    def test_http_uri_type(self):
        """Allow a single uri in either format that must be http/s"""
        valid_inputs = ['http://google.ca', {'@id': 'https://bing.com'}]
        self.assert_no_errors_with_inputs(self.base_validator._http_uri_type, valid_inputs)

        invalid_inputs = ['ftp://google.ca', ['http://google.ca', 'http://bing.ca']]
        self.assert_errors_with_inputs(self.base_validator._http_uri_type, invalid_inputs)

    def test_uri_type(self):
        """Allow a single uri in either format."""
        valid_inputs = ['http://google.ca', 'ftp://google.ca', {'@id': 'http://google.ca'}]
        self.assert_no_errors_with_inputs(self.base_validator._uri_type, valid_inputs)

        invalid_inputs = [{'key': 'http:google.ca'}, 'hello', ['http://google.ca']]
        self.assert_errors_with_inputs(self.base_validator._uri_type, invalid_inputs)

    def test_metadata_field(self):
        """Allow properly formatted metadata as specified by the presentation api."""
        valid_inputs = [
            [{'value': 'hello', 'label': 'greeting'}],
            [{'value': [{'@language': 'en', '@value': 'hello'}], 'label': 'greeting'}],
            [{'value': 'hello', 'label': {'@language': 'en', '@value': 'greeting'}}],
        ]
        self.assert_no_errors_with_inputs(self.base_validator.metadata_field, valid_inputs)

        invalid_inputs = [
            [{'bad_key': 'wow', 'this_sucks': 'yup'}],
            ['a string'],
            "a stringier string",
            [{"value": "missing label"}]
        ]
        self.assert_errors_with_inputs(self.base_validator.metadata_field, invalid_inputs)

    def test_general_image_resource(self):
        """Test correct behaviour of general image resource validation."""
        val = "http://google.ca"
        self.base_validator._general_image_resource("unknown_field", val)
        self.assertTrue(self.has_warnings())
        self.assertFalse(self.has_errors())
        self.clear_errors_and_warnings()

        val = {"@id": "http://google.ca"}
        self.base_validator._general_image_resource("unknown_field", val)
        self.assertTrue(self.has_warnings())
        self.assertFalse(self.has_errors())
        self.clear_errors_and_warnings()

        val = {"service": {"@context": "http://iiif.io/api/image/2/context.json"}}
        self.base_validator._general_image_resource("unknown_field", val)
        self.assertFalse(self.has_warnings())
        self.assertFalse(self.has_errors())


