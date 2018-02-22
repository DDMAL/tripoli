.. :changelog:

Release History
---------------

2.0.0 (2018-02-22)
++++++++++++++++++

Tripoli v2.0.0 is functionally equivalent to v1.2.2. The major version number is being incremented
to mirror the IIIF Presentation API version it supports. Tripoli v3 will only support Presentation
API v3.


1.2.1 (2017-10-11) / 1.2.2
++++++++++++++++++

**Improvements**

- Unit testing improvements and enhanced coverage
- Enhanced testing fixtures
- Travis-CI builds and Coveralls integration

**Bugfixes**

- Multiple sequences are now correctly validated.
- Canvas images are more thoroughly checked for their values.

NB: 1.2.2 is the same as 1.2.1, but incremented to try and address an issue with
distributing via PyPI.


1.2.0 (2017-05-04)
++++++++++++++++++

**Improvements**

- Configuration arguments for the basic IIIFValidator can now be passed in via kwargs
  on the `__init__` function. A validator can now be instantiated with all its settings
  in one line.

**Bugfixes**

- Web interface now specifically mentions that tripoli is for validating IIIF Manifests.

1.1.4 (2016-08-23)
++++++++++++++++++

**Bugfixes**

- Fixed an issue with the default values of REQUIRED_FIELDS (and other field sets)
  being empty dicts instead of empty sets.

1.1.3 (2016-08-23)
++++++++++++++++++

**Bugfixes**

- A warning message regarding uncertain HTML tags has been fixed to include the name
  of the tag.

1.1.2 (2016-08-22)
++++++++++++++++++

**Improvements**

- Added IIIF manifest test suite to tests, ensuring that each throws an error. A
  number of new errors and warning have been added to this end.
- Faster hash algorithms for ValidatorLogEntries increasing overall performance.
- Added HISTORY.rst to track bugfixes and improvements.
- README.rst and HISTORY.rst will be automatically read into the setup.py long_description
  field (idea taken from requests).

**Bugfixes**

- ``ViewingHint`` is now a common field which can be checked on any resource.
- ``startCanvas`` is now validated properly.
- ``Annotation`` no longer logs a warning if it has a ``@context`` field.
- ``ImageResource`` now must have ``@type`` 'dctypes:Image'.
- Presence of XML Comments or CDATA sections will cause an error to be logged.
- Fixed exception when ``IIIFValidator`` could not discern the ``@type`` of a resource.


1.1.1 (2016-08-18)
++++++++++++++++++

**Bugfixes**

- A bug was preventing ``descriptions`` from being validated in all resources.
  This has been fixed.

1.1 (2016-08-18)
++++++++++++++++

**New Features**

- Added HTML validation. This will check that only fields which are allowed
  to contain HTML have it, that the HTML is valid, and that only allowed tags
  and attributes are included.
- Added indices in error and message paths. These indices make it easier to
  figure out exactly which canvas is failing with an error (if indeed only a
  few are failing).
- Added unique/non unique error aggregation. Using a ``unique_logging` property
  on a ``IIIFValidator``, users can decide whether all errors and warnings will be
  aggregated, or only unique ones. Here, unique means that only one instance of
  each error/warning per resource will be saved (that is, if every canvas has error
  A, then only the first instance of a canvas with error A will be saved).
- Added ``verbose`` property to ``IIIFValidatior``. When ``True``, every error and
  warning will be logged immediatly to the screen when hit.

**Bugfixes**

- ``Annotations`` no longer log a warning when they are missing an ``@id`` field.
