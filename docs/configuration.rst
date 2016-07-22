Configuration
=============
Tripoli was designed to make it simple to both ignore and override validation
behaviour for particular parts of the API, and to apply corrections while
validating. These features should be useful for those implementing a service
which aggregates IIIF manifests.

Overriding Validation Behaviour
-------------------------------

Tripoli presents a class hierarchy for IIIF document validation that closely
mirrors the structure of the API documentation itself. Each major IIIF manifest resource type has a class responsible
for validating it, making it easy to override behaviour, and each field on the resource has a corresponding function
which is responsible for checking that it's value is correct and calling ``self.log_error`` or ``self.log_warning``
otherwise. On our own aggregation service, `Musiclibs <http://musiclibs.net>`_, we use this functionality to ignore
or correct systematic errors made by providers.

### Ignoring Validation Errors

To illustrate, we will use an example from our own project. We know that "Library X" has a bug
in their manifest generation software: they have incorrectly copied the url of the
presentation API context. Since this is a validation error, but does not present a problem with viewing the document,
we want to change this error to a warning. If we try to validate one of their manifests, we get the
following errors. ::

    >>> from tripoli import IIIFValidator
    >>> import requests

    >>> manifest = requests.get("http://libraryX.com/123/manifest.json").json()
    >>> iv = IIIFValidator()
    >>> iv.validate(manifest)
    >>> iv.print_errors():
    Error: '@context' must be set to 'http://iiif.io/api/presentation/2/context.json' @ data['@context']

We can inspect the manifest itself to see what the ``@context`` key is. ::

    >>> manifest.get("@context")
    'http://iiif.io/api/presentation/2/context.js'

Just as suspected, the context URI has been incorrectly copied and the last two characters of "json" are missing.

To change the validation behaviour we subclass the ``ManifestValidator``, changing the default field function for the
'@context' key to one that expects this error and compensates for it.

Here is a function that returns a IIIFValidator that will accept Library X documents. ::

    >>> from tripoli import IIIFValidator, ManifestValidator

    >>> def make_library_x_validator():
    ...     class PatchedManifestValidator(ManifestValidator):
    ...         @override
    ...         def context_field(value):
    ...             if value == 'http://iiif.io/api/presentation/2/context.js':
    ...                 self.log_warning("@context", "Allowed Library X shenanigans.")
    ...                 return value
    ...             else:
    ...                 return super().context_field(value)
    ...     iv = IIIFValidator()
    ...     iv.ManifestValidator = PatchedManifestValidator
    ...     return iv

Hopefully examining the above function will make it clear how simple it is to override behaviour
to ignore particular errors as an aggregator. Essentially, we determine on what resource the
error occurs (in this case on the top level manifest, so we import ``ManifestValidator``), then
create a subclass of that resource's validator which can allow for the error. Reading the
`API guide <api.html>`_ will clarify some of the nitty gritty of how this works.

Making Corrections
------------------

Tripoli can also make corrections to a manifest while validating. This is useful when
you are aware of a systematic error in a provider's manifests, and this does have implications
for viewing the document.
 
Each validation function (those that end with ``*_field``) must return a value. By default,
they return whatever value was passed to them, but this can easily be changed in order to
compile a corrected document.

For example, if "Library Y" sets the ``height`` and ``width`` keys of it's canvases
as strings instead of ints, you can detect this and compensate for it in the appropriate
validation functions. To handle this, we can write a new ``str_to_int`` function that attempts
to coerce ints to strings and delegate the work of the ``height_field`` and ``width_field`` functions
to it. Applying the same pattern as above: ::

    >>> from tripoli import IIIFValidator, CanvasValidator

    >>> def make_library_y_validator():
    ...     class PatchedCanvasValidator(CanvasValidator):
    ...         def str_to_int(field, value):
    ...         """Attempt to coerce value to int and log results."""
    ...             try:
    ...                 val = int(value)
    ...                 self.log_warning(field, "Coerced str to int (Library Y shenanigans)")
    ...                 return val
    ...             except ValueError:
    ...                 self.log_error(field, "Could not coerce string to int")
    ...                 return value
    ...
    ...         @override
    ...         def height_field(value):
    ...             return str_to_int("height", value)
    ...
    ...         @override
    ...         def width_field(value):
    ...             return str_to_int("width", value)
    ...
    ...     iv = IIIFValidator()
    ...     iv.CanvasValidator = PatchedCanvasValidator
    ...     return iv

When you create this validator and run it on a manifest, it will retain the corrected
document in a ``corrected_doc`` key. ::

    >>> iv = make_library_y_validator()
    >>> iv.validate(libraryY_manifest)
    >>> iv.corrected_doc # A document with the applied corrections

Configuration Tools
-------------------

A number of utility functions have been included in the ``BaseValidator`` class to simplify
common configuration jobs.

First among these are ``warnings_to_errors`` and ``errors_to_warnings`` decorators that can
be used to wrap any function and either upgrade or downgrade its logging output. As an example,
if you did not care about the thumbnails on manifests, you could easily coerce any errors found
on that field into warnings with the following ``ManifestValidator``. ::

    >>> class PatchedManifestValidator(ManifestValidator):
    ...     @ManifestValidator.errors_to_warnings
    ...     def thumbnail_field(self, value):
    ...         return super().thumbnail_field(value)

Another useful tool is the ``mute_errors`` function. Given a function and an arbitrary amount
of arguments, it will call the function on the arguments and return a 2-tuple with the return
value of the function and a set of any errors it tried to log. These errors will not be logged
and will not trigger a failure of the validation. The following example accomplishes the same
goal as the one above ::

    >>> class PatchedManifestValidator(ManifestValidator):
    ...     def thumbnail_field(self, value):
    ...         val, errs = self.mute_errors(super().thumbnail_field, value)
    ...         for err in errors:
    ...             self.log_warning('thumbnail', err.message)
    ...         return val

When implementing a corrective or overriding behaviour, it may be difficult to figure
out exactly which function needs to be overridden. In this case, setting ``debug`` to
``true`` on your ``IIIFValidator`` will include tracebacks with your errors and warnings,
which can be inspected to figure out which function logged them.