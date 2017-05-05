try:
    import ujson as json
except ImportError:
    import json

import os

from .validator_testing_tools import ValidatorTestingTools
from tripoli import IIIFValidator


class TestIIIFValidator(ValidatorTestingTools):
    def setUp(self):
        self.test_subject = IIIFValidator()
        self.test_subject.logger.setLevel("CRITICAL")
        self.test_subject.fail_fast = False
        self.test_subject.collect_errors = True
        self.test_subject.collect_warnings = True
        self.test_subject.debug = True

        self.base_dir = os.path.dirname(os.path.realpath(__file__))

        with open(os.path.join(self.base_dir, 'fixtures/valid_manifest')) as f:
            self.valid_manifest = json.load(f)

        with open(os.path.join(self.base_dir, 'fixtures/error_collection.json')) as f:
            self.error_collection = json.load(f)
            self.man_with_warnings_and_errors = self.error_collection['manifests'][-1]['manifest']

    def test_valid_manifest(self):
        """Test that a valid manifest raises no errors."""
        with open(os.path.join(self.base_dir, 'fixtures/valid_manifest')) as f:
            man = json.load(f)
            self.test_subject.validate(man)
        self.assertFalse(self.has_errors())

    def test_text_manifest(self):
        """Test that a manifest can be passed as text."""
        with open(os.path.join(self.base_dir, 'fixtures/valid_manifest')) as f:
            self.test_subject.validate(f.read())
        self.assertFalse(self.has_errors())

    def test_debug_setting(self):
        """Test that the debug setting works."""
        iv = IIIFValidator(debug=True)
        iv.validate(self.man_with_warnings_and_errors)
        self.assertTrue(bool(iv.errors[0]._tb))

        iv = IIIFValidator(debug=False)
        iv.validate(self.man_with_warnings_and_errors)
        self.assertFalse(bool(iv.errors[0]._tb))

    def test_collect_warnings_setting(self):
        """Test that collect_warnings setting works."""
        iv = IIIFValidator(collect_warnings=False)
        iv.validate(self.man_with_warnings_and_errors)
