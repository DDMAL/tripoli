import unittest
import inspect


class ValidatorTestingTools(unittest.TestCase):

    def setUp(self):
        self.test_subject = None
        raise NotImplemented

    def has_error(self, error):
        """Check if a particular error was raised."""
        return error in self.test_subject._errors

    def has_errors(self):
        return bool(self.test_subject._errors)

    def has_warning(self, warning):
        return warning in self.test_subject._warnings

    def has_warnings(self):
        return bool(self.test_subject._warnings)

    def has_warnings_or_errors(self):
        return (bool(self.test_subject._warnings) or bool(self.test_subject._errors))

    def clear_errors(self):
        self.test_subject._errors = set()

    def clear_warnings(self):
        self.test_subject._warnings = set()

    def clear_errors_and_warnings(self):
        self.test_subject._errors = set()
        self.test_subject._warnings = set()

    def assert_no_errors_with_inputs(self, fn, inputs):
        """Run validation fn on each input, asserting no error is logged."""
        args = inspect.signature(fn).parameters
        for arg in inputs:
            val = fn('unknown_field', arg) if "field" in args else fn(arg)
            try:
                self.assertFalse(self.has_errors(), "{} is not valid input".format(arg))
                self.assertEqual(arg, val)
            finally:
                self.clear_errors()

    def assert_errors_with_inputs(self, fn, inputs):
        args = inspect.signature(fn).parameters
        for arg in inputs:
            val = fn('unknown_field', arg) if "field" in args else fn(arg)
            try:
                self.assertTrue(self.has_errors(), "{} is valid input".format(arg))
                self.assertEqual(arg, val)
            finally:
                self.clear_errors()

    def fake_valid(self, value):
        return value

    def fake_invalid(self, value):
        self.test_subject.log_error("fake field", "test error")
        return value

    def fake_change(self, value):
        return str(value) + "changed stuff"
