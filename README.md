Tripoli is a validator for documents conforming to the [IIIF presentation API 2.1](http://iiif.io/api/presentation/2.1/). It makes it easy to validate documents, apply provider specific heuristics, and even correct documents while they are being validated.

###Installation
You can install Tripoli using pip.
```
> pip install tripoli
```

###Quick start
Once installed, it's easy to start validating. Tripoli can validate the entire document, and will log informative errors and warnings with helpful paths.
```
>>> from tripoli import IIIFValidator

>>> iv = IIIFValidator()
>>> iv.validate(some_manifest)
    Error: Field has no '@language' key where one is required. @ data['metadata']['value']
    Error: viewingHint 'pages' is not valid and not uri. @ data['sequences']['canvases']['viewingHint']
    Warning: logo SHOULD be IIIF image service. @ data['logo']
    Warning: manifest SHOULD have thumbnail field. @ data['thumbnail']
    Warning: Unknown key 'see_also' in 'manifest' @ data['see_also']
    Warning: ImageResource SHOULD have @id field. @ data['sequences']['canvases']['images']['@id']
```

###Documentation
Detailed documentation is available at http://tripoli.readthedocs.io/en/latest/