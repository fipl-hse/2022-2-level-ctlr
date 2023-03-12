# Article package

The Article package exposes a class `Article` that models web article that is
downloaded and parsed. It is responsible for storing article information:
`url`, `id`, `title`, `author`, `topics`, `raw text`, and `part-of-speech (POS) frequency information`.

The class also provides methods to get and set various attributes of the article object,
as well as methods to retrieve file paths for various types of artifacts associated with the article.

The package also defines an `ArtifactType` `enum` that represents the types of artifacts that
can be created by text processing pipelines, such as `cleaned text`, `morphological analysis` data in
CoNLL-U format, and `full CoNLL-U annotation` data.

Feel free to inspect its content. In case you think you have found a mistake, contact
assistant. Those who considerably improve this module will get additional 
bonuses.

# I/O module

Functions from this module can help you load meta.json file 
into the `Article` abstraction and saving article in `raw` and `meta` formats. 
> **HINT:** for `Crawler` implementation, you need the following methods:
> * `Article.__init__(...)`
> * `to_raw(Article)`
> * `to_meta(Article)`

> **HINT:** for `Pipeline` implementation you need following methods:
> * `to_raw(Article)`
> * `to_meta(Article)`

> **HINT:** In order to save processed versions of files you must utilize attributes of `ArtifactType`. 
> Otherwise, if you pass to some saving function a string itself, your code will be much more fragile. 
