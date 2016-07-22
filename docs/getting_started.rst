Getting Started
===============

Installing
----------

Validation
----------
Using Tripoli to validate a IIIF document is easy. ::

    >>> from tripoli import IIIFValidator
    >>> import requests # for example

    >>> iv = IIIFValidator()
    >>> manifest = requests.get("http://example.com/manifest.json")
    >>> iv.validate(manifest.text)
    >>> iv.is_valid
    True

When Tripoli detects issues in a document, it provides informative errors and warnings with
key paths to simplify the debugging progress. ::

    >>> man = requests.get("http://example.com/bad_manifest.json")
    >>> iv.validate(man)
    >>> iv.is_valid
    False

    >>> iv.print_warnings()
    Warning: logo SHOULD be IIIF image service. @ data['logo']
    Warning: manifest SHOULD have thumbnail field. @ data['thumbnail']
    Warning: Unknown key 'see_also' in 'manifest' @ data['see_also']
    Warning: ImageResource SHOULD have @id field. @ data['sequences']['canvases']['images']['@id']

    >>> iv.print_errors()
    Error: Field has no '@language' key where one is required. @ data['metadata']['value']
    Error: viewingHint 'pages' is not valid and not uri. @ data['sequences']['canvases']['viewingHint']

Options
-------
The ``IIIFValidator`` has a number of options to control its behaviour.

.. module:: tripoli
.. autoclass:: IIIFValidator
    :noindex:
    :members: collect_errors, collect_warnings, debug, fail_fast

The complete interface can be found in the :doc:`api guide </api>`.

Tripoli can also be configured to log extra warnings, ignore particular
errors, and correct errors in manifests. Refer to the :doc:`configuration section</configuration>`
for more information.
