Getting Started
===============

Installing
----------
Tripoli can by installed using ``pip``. ::

    >>> pip install tripoli

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

The complete interface can be found in the :doc:`API guide </api>`.

Tripoli can also be configured to log extra warnings, ignore particular
errors, and correct errors in manifests. Refer to the :doc:`configuration section</configuration>`
for more information.


Validating Online
-----------------

You can use tripoli to validate online at https://validate.musiclibs.net. Simply pass in a link to a manifest
as a query parameter named 'manifest'. ::

    >>> curl "https://validate.musiclibs.net/?manifest=${MANIFEST_URL}" -H "Accept: application/json"
    {
      "errors": [
        "Error: '@context' must be set to 'http://iiif.io/api/presentation/2/context.json' @ data['@context']",
        "Error: @context field not allowed in embedded sequence. @ data['sequences']['@context']",
        "Error: Key 'on' is required in 'annotation' @ data['sequences']['canvases']['images']['on']"
      ],
      "is_valid": false,
      "manifest_url": ${MANIFEST_URL},
      "warnings": [
        "Warning: thumbnail SHOULD be IIIF image service. @ data['thumbnail']",
        "Warning: manifest SHOULD have description field. @ data['description']",
        "Warning: logo SHOULD be IIIF image service. @ data['logo']",
        "Warning: Unknown key '@context' in 'sequence' @ data['sequences']['@context']",
        "Warning: Unknown key '@context' in 'annotation' @ data['sequences']['canvases']['images']['@context']"
      ]
    }

