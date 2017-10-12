from .validator_testing_tools import ValidatorTestingTools
from tripoli import IIIFValidator
from tripoli.resource_validators.base_validator import BaseValidator
from tripoli.validator_logging import ValidatorLogError, ValidatorLogWarning, ValidatorLog, Path
from tripoli.exceptions import FailFastException


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
                        [{'@language': 'en', '@value': 'hello'}, {'@language': 'fr', '@value': 'bonjour'}],
                        {'@value': 'Hello'}]
        self.assert_no_errors_with_inputs(self.test_subject._str_or_val_lang_type, valid_inputs)

        invalid_inputs = [0, {'@value': 14, '@language': 'en'}, ]
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

        val = {"@id": "http://google.ca",
               "@type": "dctypes:Image",
               "service": {"@context": "http://iiif.io/api/image/2/context.json",
                           "@id": "http://google.ca",
                           "profile": "http://google.ca"}}
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

    def test_html_validation(self):
        # Valid (path, field, html-value) tuples
        valid_inputs = {
            (Path(('metadata',)), 'label', "<a href='http://google.ca'>Google</a>"),
            (Path(('sequences', 0, 'metadata')), 'value', "<span><p>Test</p></span>"),
            (Path(tuple()), 'description', "<p><br/></p>"),
            (Path(tuple()), 'attribution', "<img src='fake source'/>")
        }

        for p, f, v in valid_inputs:
            self.test_subject._path = p
            self.test_subject._check_html(f, v)
            self.assertFalse(self.has_warnings_or_errors(), (p,v,f))

        # Invalid (path, field, html-value) tuples
        invalid_inputs = {
            (Path(tuple()), 'label', "<a href='http://google.ca'>Bad field</a>"),
            (Path(tuple()), 'description', "<script>Nasty scripting</script>"),
            (Path(tuple()), 'description', "<a target='something'>Bad attribute</a>"),
            (Path(tuple()), 'description', "this is <a>badly formatted.</a>"),
        }

        for p, f, v in invalid_inputs:
            self.test_subject._path = p
            self.test_subject._check_html(f, v)
            self.assertTrue(self.has_errors(), (p,f,v))
            self.clear_errors_and_warnings()

    def test_mute_error(self):
        # Test error is caught.
        val, err = self.test_subject.mute_errors(self.fake_invalid, "value")
        self.assertIn(ValidatorLogError('test error', ('fake field',)), err)
        self.assertFalse(self.has_errors())

        # Test fail fast is not triggered.
        self.test_subject._IIIFValidator.fail_fast = True
        try:
            val, err = self.test_subject.mute_errors(self.fake_invalid, "value")
        except FailFastException:
            self.fail("FailFastException was raised.")
        self.assertIn(ValidatorLogError('test error', ('fake field',)), err)
        self.assertFalse(self.has_errors())

    def test_error_to_warning(self):
        @self.test_subject.errors_to_warnings
        def log_error(self, value):
            self.log_error("fake field", "test error")

        # Test that error was converted to warning properly.
        log_error(self.test_subject, "value")
        self.assertFalse(self.has_errors())
        self.assertTrue(self.has_warnings())
        self.assertEqual(self.test_subject.warnings.pop(), ValidatorLogWarning('test error', ('fake field',)))

        # Test that fail fast is not triggered.
        self.test_subject._IIIFValidator.fail_fast = True
        try:
            log_error(self.test_subject, "value")
        except FailFastException:
            self.fail("FailFastException was raised.")
        self.assertTrue(self.has_warnings())
        self.assertFalse(self.has_errors())

    def test_warning_to_error(self):
        @self.test_subject.warnings_to_errors
        def log_warning(self, value):
            self.log_warning("fake field", "test error")

        # Test that warning is converted to error properly
        log_warning(self.test_subject, "value")
        self.assertTrue(self.has_errors())
        self.assertFalse(self.has_warnings())
        self.assertEqual(self.test_subject.errors.pop(), ValidatorLogError('test error', ('fake field',)))

    def test_path_equality(self):
        a = Path(('sequences', 0, 'metadata'))
        b = Path(('sequences', 0, 'metadata'))
        self.assertTrue(a == b)

    def test_path_repr(self):
        a = Path(('sequences', 0, 'metadata'))
        self.assertEqual(repr(a), "Path('sequences', 0, 'metadata')")

    def test_path_add(self):
        a = Path(('sequences', 0, 'metadata'))
        b = Path(('sequences', 0, 'metadata'))
        self.assertEqual(repr(a + b), "Path('sequences', 0, 'metadata', 'sequences', 0, 'metadata')")

    def test_path_raises_typeerror(self):
        a = Path(('sequences', 0, 'metadata'))
        b = {'foo': 'bar'}
        with self.assertRaises(TypeError):
            a + b

    def test_path_returns_path(self):
        a = Path(('sequences', 0, 'metadata'))
        self.assertEqual(a.path, ('sequences', 0, 'metadata'))

    def test_no_index_path_eq(self):
        a = Path(('sequences', 0, 'metadata'))
        b = Path(('sequences', 1, 'metadata'))
        self.assertTrue(a.no_index_eq(b))

    def test_no_index_endswith(self):
        a = Path(('sequences', 0, 'metadata', 1))
        b = Path(('sequences', 1, 'metadata'))
        self.assertTrue(a.no_index_endswith(b))

    def test_validator_log_lt(self):
        x = ValidatorLogWarning('test error', ('fake field',))
        y = ValidatorLogError('test error', ('fake field', 'another'))
        self.assertTrue(x < y)

    def test_validator_log_warning(self):
        x = ValidatorLogWarning('test error', ('fake field',))
        self.assertEqual(str(x), "Warning: test error @ data['fake field']")

    def test_validator_log_warning_repr(self):
        x = ValidatorLogWarning('test error', ('fake field',))
        self.assertEqual(repr(x), "ValidatorLogWarning('test error',  @ data['fake field'])")

    def test_validator_log_error_repr(self):
        x = ValidatorLogError('test error', ('fake field',))
        self.assertEqual(repr(x), "ValidatorLogError('test error',  @ data['fake field'])")

    # NB: This should be tested with an actual traceback scenario.
    def test_validator_log_print_trace(self):
        x = ValidatorLogError('test error', ('fake field',))
        self.assertIsNone(x.print_trace())

    def test_validator_log_raises_typeerror_on_bad_add(self):
        v = ValidatorLog()
        with self.assertRaises(TypeError):
            v.add("foo")

    def test_validator_unique_logging(self):
        v = ValidatorLog(unique_logging=False)
        e = ValidatorLogError('test error', ('fake field',))
        v.add(e)
        self.assertEqual(len(v._entries), 1)


