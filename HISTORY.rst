.. :changelog:

Release History
---------------

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
