import json
import os

from .validator_testing_tools import ValidatorTestingTools
from tripoli import IIIFValidator


class TestErrorCollection(ValidatorTestingTools):

    def setUp(self):
        self.test_subject = IIIFValidator()
        self.test_subject.logger.disabled = True
        self.base_dir = os.path.dirname(os.path.realpath(__file__))

    def test_error_collection(self):

        with open(os.path.join(self.base_dir, 'fixtures/error_collection.json')) as f:
            collection = json.load(f)

        for m in collection['manifests']:
            self.test_subject.validate(m['manifest'])
            self.assertTrue(self.has_errors(), "Did not catch error on '{}'".format(m['label']))
            self.clear_errors_and_warnings()
