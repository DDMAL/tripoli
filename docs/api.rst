API Guide
=========

Main Validator
--------------
The ``IIIFValidator`` is the root validator, responsible for storing all settings
and references to IIIF resource validators. If you are only using Tripoli to debug your own
manifest creation algorithms, it should be the only class you need to know about.

.. module:: tripoli
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
requires a reference to a ``IIIFValidator`` to be initialized, as all settings and
references to *other* validators are held therein.

.. automodule:: tripoli.resource_validators
.. autoclass:: BaseValidator
    :members:
    :inherited-members:

.. autoclass:: ManifestValidator
    :members:
    :show-inheritance:

.. autoclass:: SequenceValidator
    :members:
    :show-inheritance:

.. autoclass:: CanvasValidator
    :members:
    :show-inheritance:

.. autoclass:: AnnotationValidator
    :members:
    :show-inheritance:

.. autoclass:: ImageContentValidator
    :members:
    :show-inheritance: