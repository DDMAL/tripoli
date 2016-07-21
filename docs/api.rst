API Guide
=========

Main Validator
--------------
The ``IIIFValidator`` is responsible for storing all settings and references
to IIIF resource validators. If you are only using tripoli to debug your own
manifest creation algorithms, it should be the only class you need to know about.

.. module:: tripoli.tripoli
.. autoclass:: IIIFValidator
    :members:
    :inherited-members:

Error and Warning Logging
-------------------------
.. module:: tripoli.validator_logging
.. autoclass:: ValidatorLogError
    :members: print_trace
    :inherited-members: msg, path
.. autoclass:: ValidatorLogWarning
    :members: print_trace
    :inherited-members: msg, path

IIIF Resource Validators
------------------------
All validators inherit from the ``BaseValidator`` class. This, and all validators,
requires a reference to a ``IIIFValidator`` to be initiated, as all settings and
references to *other* validators are held therein.

.. module:: tripoli.iiif_resource_validators
.. autoclass:: BaseValidator
    :members:
    :inherited-members:

