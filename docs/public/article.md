# Article module

The Article module exposes a class `Article` that models web article that is
downloaded and parsed. It is responsible for several aspects:

1. Storing article information: url, id, title, etc.
1. File I/O (stands for Input/Output): reading and writing of article raw text,
   processed text and its meta-information

This module is functional and given to you for further usage. Feel free to 
inspect its content. In case you think you have found a mistake, contact
assistant. Those who considerably improve this module will get additional 
bonuses.

> **HINT:** for `Crawler` implementation, you need the following methods:
> * `Article.__init__(...)`
> * `Article.save_raw(...)`

> **HINT:** for `Pipeline` implementation you need following methods:
> * `Article.get_raw_text(...)`
> * `Article.save_processed_as(...)`

> **HINT:** In order to save processed versions of files you must utilize attributes of `ArtifactType`. 
> Otherwise, if you pass to `Article.save_processed_as(...)` a string itself, your code will be much more fragile. 
