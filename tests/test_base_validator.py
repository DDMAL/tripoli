from tests.validator_tester import ValidatorTestingTools
from tripoli import IIIFValidator
from tripoli.iiif_resource_validators.base_validator import BaseValidator


class TestBaseValidatorMixin(ValidatorTestingTools):

    def setUp(self):
        iv = IIIFValidator()
        iv.fail_fast = False
        iv.collect_errors = True
        iv.collect_warnings = True
        iv.debug = False
        self.test_subject = BaseValidator(iv)

    def test_compare_dicts(self):
        man = {"field_1": "value", "field_3": "value"}

        # Test that nothing is changed in valid case.
        schema = {"field_1": self.fake_valid, "field_2": self.fake_valid}
        val = self.test_subject._compare_dicts(schema, man)
        self.assertFalse(self.has_errors())
        self.assertEqual(man, val)
        self.clear_errors_and_warnings()

        # Test that warning is logged in invalid case.
        schema = {"field_1": self.fake_invalid, "field_2": self.fake_valid}
        val = self.test_subject._compare_dicts(schema, man)
        self.assertEqual(man, val)
        self.assertTrue(self.has_errors())
        self.clear_errors_and_warnings()

        # Test that making a change does not affect original argument.
        schema = {"field_1": self.fake_change}
        old_man = man.copy()
        val = self.test_subject._compare_dicts(schema, man)
        self.assertEqual(old_man, man)
        self.assertNotEqual(val, man)

    def check_recommended_fields(self):
        # Test a warning comes through when missing a recommended field.
        self.test_subject._check_recommended_fields("test", {}, ["test_field"])
        self.assertTrue(self.has_warnings())
        self.clear_errors_and_warnings()

        # Test no warning when all recommended fields are there.
        self.test_subject._check_recommended_fields("test", {"test_field": "value"}, ["test_field"])
        self.assertFalse(self.has_warnings())

    def check_unknown_fields(self):
        # Test a warning comes through when an unknown field is included.
        self.test_subject._check_unknown_fields("test", {"other_field": "value"}, ["test_field"])
        self.assertTrue(self.has_warnings())
        self.clear_errors_and_warnings()

        # Test no warning when all fields are known.
        self.test_subject._check_unknown_fields("test", {"test_field": "value"}, ["test_field"])
        self.assertFalse(self.has_warnings())

    def check_forbidden_fields(self):
        # Test an error comes through when forbidden field is included.
        self.test_subject._check_forbidden_fields("test", {"test_field": "value"}, ["test_field"])
        self.assertTrue(self.has_errors())
        self.clear_errors_and_warnings()

        # Test no error when no fields are forbidden.
        self.test_subject._check_forbidden_fields("test", {"other_field": "value"}, ["test_field"])
        self.assertFalse(self.has_errors())

    def check_required_fields(self):
        # Test an error comes through when a required field is missing.
        self.test_subject._check_required_fields("test", {"other_field": "value"}, ["test_field"])
        self.assertTrue(self.has_errors())
        self.clear_errors_and_warnings()

        # Test no error when all required fields are included.
        self.test_subject._check_required_fields("test", {"test_field": "value"}, ["test_field"])
        self.assertFalse(self.has_errors())

    def test_str_or_val_lang_type(self):
        """Allows stings, lists of strings, val/lang dicts, and lists of val/lang dicts"""
        valid_inputs = ['hello', ['hello', 'there'], {'@language': 'en', '@value': 'hello'},
                        [{'@language': 'en', '@value': 'hello'}, {'@language': 'fr', '@value': 'bonjour'}]]
        self.assert_no_errors_with_inputs(self.test_subject._str_or_val_lang_type, valid_inputs)

        invalid_inputs = [0, {'@value': 14, '@language': 'en'}, {'@value': 'Hello'}]
        self.assert_errors_with_inputs(self.test_subject._str_or_val_lang_type, invalid_inputs)

    def test_repeatable_str_type(self):
        """Allows strings or lists of strings."""
        valid_inputs = ['hello', ['hello', 'there']]
        self.assert_no_errors_with_inputs(self.test_subject._repeatable_string_type, valid_inputs)

    def test_repeatable_uri_type(self):
        """Allow a single uri or list of uris (in both uri formats)"""
        valid_inputs = ['http://google.ca', ['http://google.com', {'@id': 'http://bing.com'}]]
        self.assert_no_errors_with_inputs(self.test_subject._repeatable_uri_type, valid_inputs)

        invalid_inputs = ['hello', ['hello', 'everyone']]
        self.assert_errors_with_inputs(self.test_subject._repeatable_uri_type, invalid_inputs)

    def test_http_uri_type(self):
        """Allow a single uri in either format that must be http/s"""
        valid_inputs = ['http://google.ca', {'@id': 'https://bing.com'}]
        self.assert_no_errors_with_inputs(self.test_subject._http_uri_type, valid_inputs)

        invalid_inputs = ['ftp://google.ca', ['http://google.ca', 'http://bing.ca']]
        self.assert_errors_with_inputs(self.test_subject._http_uri_type, invalid_inputs)

    def test_uri_type(self):
        """Allow a single uri in either format."""
        valid_inputs = ['http://google.ca', 'ftp://google.ca', {'@id': 'http://google.ca'}]
        self.assert_no_errors_with_inputs(self.test_subject._uri_type, valid_inputs)

        invalid_inputs = [{'key': 'http:google.ca'}, 'hello', ['http://google.ca']]
        self.assert_errors_with_inputs(self.test_subject._uri_type, invalid_inputs)

    def test_metadata_field(self):
        """Allow properly formatted metadata as specified by the presentation api."""
        valid_inputs = [
            [{'value': 'hello', 'label': 'greeting'}],
            [{'value': [{'@language': 'en', '@value': 'hello'}], 'label': 'greeting'}],
            [{'value': 'hello', 'label': {'@language': 'en', '@value': 'greeting'}}],
        ]
        self.assert_no_errors_with_inputs(self.test_subject.metadata_field, valid_inputs)

        invalid_inputs = [
            [{'bad_key': 'wow', 'this_sucks': 'yup'}],
            ['a string'],
            "a stringier string",
            [{"value": "missing label"}]
        ]
        self.assert_errors_with_inputs(self.test_subject.metadata_field, invalid_inputs)

    def test_general_image_resource(self):
        """Test correct behaviour of general image resource validation."""
        val = "http://google.ca"
        self.test_subject._general_image_resource("unknown_field", val)
        self.assertTrue(self.has_warnings())
        self.assertFalse(self.has_errors())
        self.clear_errors_and_warnings()

        val = {"@id": "http://google.ca"}
        self.test_subject._general_image_resource("unknown_field", val)
        self.assertTrue(self.has_warnings())
        self.assertFalse(self.has_errors())
        self.clear_errors_and_warnings()

        val = {"service": {"@context": "http://iiif.io/api/image/2/context.json"}}
        self.test_subject._general_image_resource("unknown_field", val)
        self.assertFalse(self.has_warnings())
        self.assertFalse(self.has_errors())

    def test_view_dir_hint_field(self):
        self.test_subject.VIEW_HINTS = {"paged", "non-paged"}
        self.test_subject.VIEW_DIRS = {"paged", "non-paged"}
        self.assert_no_errors_with_inputs(self.test_subject.viewing_hint_field, ["paged", "non-paged"])
        self.assert_errors_with_inputs(self.test_subject.viewing_hint_field, ["error"])
        self.assert_no_errors_with_inputs(self.test_subject.viewing_dir_field, ["paged", "non-paged"])
        self.assert_errors_with_inputs(self.test_subject.viewing_dir_field, ["error"])