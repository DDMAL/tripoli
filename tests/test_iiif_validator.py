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

