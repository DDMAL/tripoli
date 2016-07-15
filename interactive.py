import IPython
import json
from tripoli import IIIFValidator

with open("test_manifests/ecodes") as f:
    ecodes = json.load(f)
iv = IIIFValidator()
IPython.embed()