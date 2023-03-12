# Retrieve raw data from World Wide Web

> Python competencies required to complete this tutorial:
> * working with external dependencies, going beyond Python standard library
> * working with external modules: local and downloaded from PyPi
> * working with files: create/read/update
> * downloading web pages
> * parsing web pages as HTML structure

Scraping as a process contains the following steps:
1. crawling the web-site and collecting all pages that satisfy criteria given
1. downloading selected pages content
1. extracting specific content from pages downloaded
1. saving necessary information

As a part of the first milestone, you need to implement scrapping logic as a `scrapper.py` module. When it is run as a standalone Python program, it should perform all aforementioned stages.

## Executing scrapper

Example execution (`Windows`):

```bash
python scrapper.py
```

Expected result:
1. `N` articles from the given URL are parsed
1. all articles are downloaded to the `tmp/articles` directory. `tmp` directory should conform to the following structure:

```
+-- 2022-2-level-ctlr
    +-- tmp
        +-- articles
            +-- 1_raw.txt     <- the paper with the ID as the name
            +-- 1_meta.json   <- the paper meta-information
            +-- ...
```

> NOTE: When using CI (Continuous Integration), generated `raw-dataset.zip` is available in
> build artifacts. Go to `Actions` tab in GitHub UI of your fork, open the last job and
> if there is an artifact, you can download it.

## Configuring scrapper

Scrapper behavior is fully defined by a configuration file that is called `scrapper_config.json` and it is placed at the same level as `scrapper.py`. It is JSON file, simply speaking it is a set of key-value pairs.

|Config parameter|Description|Possible values|
|:---|:---|:---|
|`seed_urls`| Entry points for crawling. Can contain several URLs as there is no guarantee that there will be enough article links on a single page|A list of URLs, for example `["https://www.nn.ru/text/?page=2", "https://www.nn.ru/text/?page=3"]`|
|`headers`| Headers let you pass additional information within request to the web page. Usually they help to identify your program as real browser and get access to the site. They are not obligatory, but if you face troubles sending request to the web page, you may need to use headers. |Headers are represented as string with the following format, for example `{'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36'}`. **Hint:** you may find special websites that generate headers appropriate for you computer and web browser.|
|`total_articles_to_find_and_parse`|Number of articles to parse|Integer values, should potentially work for at least `100` papers, but must not be too big|
|`encoding`| This parameter specifies encoding for the response received by the web page you request. | This is a string, for example `utf-8`.|
|`timeout`| The amount of time you wait for a response from your web page. If the page does not respond in the specified time, an exception will be received.| This is an integer, for example `5`.|
|`should_verify_certificate`| Parameter that enables or disables the security certificate check of your requests to the page. Disable it if you cannot pass web page security certification. | It is a boolean value, for example `true`.|
|`headless_mode`| This parameter enables or disables headless mode and is appropriate only for dynamic websites crawling. **Note:** You may set it to `true` to see how you program interacts with website, but make sure you disable it before pushing your changes to GitHub. | It is a boolean value, for example `false`.|

> NOTE: `seed_urls` and `total_articles_to_find_and_parse` are used in `Crawler` abstraction. `headers`, `encoding`, `timeout`, `should_verify_certificate` are used in `make_request` function. `headless_mode` is used only if you work with dynamic websites. See definition and requirements for these abstractions and functions within further steps.

## Assessment criteria

You state your ambitions on the mark by editing the file `lab_5_scrapper/target_score.txt`. Possible values are `4`, `6`, `8`, and `10`. See example below:

```
6
```

would mean that you have made tasks for mark `6` and request mentors to check if you can get it. See mark requirements and explanations below:

1. Desired mark: **4**:
   1. `pylint` level: `5/10`;
   1. scrapper validates config and fails appropriately if the latter is incorrect;
   1. scrapper downloads articles from the selected newspaper;
   1. scrapper produces only `_raw.txt` files in the `tmp/articles` directory (*no metadata files*);
1. Desired mark: **6**:
   1. `pylint` level: `7/10`;
   1. all requirements for the mark **4**;
   1. scrapper produces `_meta.json` files for each article, however, it is allowed for each
      meta file to contain reduced number of keys: `id`, `title`, `author`, `url`;
1. Desired mark: **8**:
   1. `pylint` level: `10/10`;
   2. all requirements for the mark **6**;
   3. scrapper produces `_meta.json` files for each article, meta file should be full: 
      `id`, `title`, `author`, `url`, `date`, `topics`. In contrast to the task for mark **6**,
       it is mandatory to collect a date for each of the articles in the appropriate format.
1. Desired mark: **10**:
   1. `pylint` level: `10/10`;
   1. all requirements for the mark **8**;
   1. given just one seed url, crawler can find and visit all website pages requested.

> NOTE: date should be in the special format. Read [dataset description](../docs/public/dataset.md) for technical details

## Implementation tactics

> NOTE: all logic for instantiating and using needed abstractions should be implemented in a special block of the module `scrapper.py`

```py
if __name__ == '__main__':
   print('Your code goes here')
```

### Stage 0. Choose the media

Start your implementation by selecting a website you are going to scrap. Pick the website that interests you the most. If you plan on working on a mark higher than **4**, make sure all the necessary information is present on your chosen website. Read more in the [course overview](../README.md) in the milestones section.

### Stage 1. Extract and validate config first

#### Stage 1.1 Use `ConfigDTO` abstraction

You are provided with the `ConfigDTO` abstraction. It is located in [`core_utils` folder](../core_utils/config_dto.py).
Use it to store you scrapper configuration data from `scrapper_config.json`. Examine class fields closely.

For more information about DTO object fields refer to description of scrapper configuration parameters above.

> Tip: DTO is a short for Data Transfer Object. It is commonly used term and programming pattern.  You may read more about DTO [here](https://www.okta.com/identity-101/dto/).

#### Stage 1.2 Introduce Config abstraction

To be able to read, validate, and use scrapper configuration data inside your program you need to implement special `Config` abstraction that is responsible for extracting and validating data from `scrapper_config.json` file.

Interface to implement:

```py
class Config:
   pass
```

See example call:

```py
configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
```

where `CRAWLER_CONFIG_PATH` is the path to the config of the crawler. It is mandatory to initialize `Config` class instance with passing a global variable `CRAWLER_CONFIG_PATH` that should be properly imported from the [`constants.py`](../core_utils/constants.py) module.

#### Stage 1.3 Extract configuration data

To be able to use scrapper configuration data inside your program you need to define a method inside `Config` class for extracting configuration data. See interface below:

```py
class Config:
   ...
   def _extract_config_content(self):
      pass
```

The method should open configuration file, create and fill the `ConfigDTO` instance with all configuration parameters filled.

The method should return an instance of the `ConfigDTO` class with configuration parameters filled.

> NOTE: this method should be called during `Config` class instance initialization step to fill fields with configuration parameters information.

#### Stage 1.4 Validate configuration data

The `Config` class is responsible not only for configuration data extraction, but for its validation as well. Hence you need to implement a validation method too. See interface definition below:

```py
class Config:
   ...
   def _validate_config_content(self):
      pass
```

This method returns nothing.

Inside the method you need to define and check formal criteria for valid configuration. When config is invalid:

1. one of the following errors is thrown (each exception description can be found in `scrapper.py`):
   `IncorrectSeedURLError`, `NumberOfArticlesOutOfRangeError`, `IncorrectNumberOfArticlesError`, `IncorrectHeadersError`,
   `IncorrectEncodingError`, `IncorrectTimeoutError`, `IncorrectVerifyError`, 
2. script immediately finishes execution

When all validation criteria are passed there is no exception thrown and program continues its execution.

> NOTE: this method should be called during `Config` class instance initialization step before the `_extract_config_content` method call to check config fields and make sure they are appropriate and can be used inside the program.

#### Stage 1.5 Provide getting methods for configuration parameters

To be able to further use configuration data extracted across your program you need to specify methods for getting each configuration parameter. For example:

```py
def get_seed_urls(self):
   pass
```

The method above defined inside the `Config` class should return seed urls value from scrapper config file extracted when needed. Similar methods should be defined for all scrapper configuration parameters that you will be using across the program.

### Stage 2 Set up work environment

#### Stage 2.1 Set up folder for articles

When config is correct (the `Config` class instance is initialized meaning config is valid and loaded inside the program), you should prepare appropriate environment for your scrapper to work. Basically, you must check that a directory provided by `ASSETS_PATH` does in fact exist and is empty. In order to do that, implement the following function:

```py
def prepare_environment(base_path):
    pass
```
It is mandatory to call this function after the config file is validated and before crawler is run.

> NOTE: If folder specified by `ASSETS_PATH` is already created and filled with some files (e.g. from your previous scrapper run) you need to remove the existing folder and then create an empty folder with this name in current method

#### Stage 2.2. Set up website requesting function

You will need to make requests inside you program to the website several times during each scrapper run, so it is wise to create service function making request to your website for reusing across program when needed. See the interface suggestion below:

```py
def make_request(url: str, config: Config):
    pass
```

The first ``url`` parameter specifies URL you want to send request to.

The second ``config`` parameter is an instance of the `Config` class you initialized previously.

> HINT: Inside this function use config getting methods  that you should have defined previously inside the `Config` class to get request configuration parameters, for example `config.get_timeout()` to get timeout value.

The function should return response from the request.

### Stage 3. Find necessary number of article URLs

#### Stage 3.1 Introduce Crawler abstraction

Crawler is an entity that visits `seed_urls` with the intention to collect
URLs of the articles that should be parsed later.

> **seed url** - this is a known term, you can read more in 
> [Wikipedia](https://en.wikipedia.org/wiki/Web_crawler#Overview) or any other more reliable source of information
> you trust.

Crawler should be instantiated with the following instruction:

```py
crawler = Crawler(config=configuration)
```

Crawler instance saves provided configuration instance in an attribute with the corresponding name. Each instance should also have an
additional attribute `self.urls`, initialized with empty list.

#### Stage 3.2 Implement a method for collecting article URLs

Once the crawler is instantiated, it can be started by executing its 
method:

```py
crawler.find_articles()
```

The method should iterate over the list of seeds, 
download them and extract article URLs from it. As a result, 
the internal attribute `self.urls` should be filled with collected URLs.

> NOTE: each URL in `self.urls` should be a valid URL, not just a suffix. For example,
> we need `https://www.nn.ru/text/transport/2022/03/09/70495829/` instead of `text/transport/2022/03/09/70495829/`.

Method `find_articles` must call another method of Crawler: `_extract_url`.
This method is responsible for retrieving a URL from HTML of the page.
Make sure that `find_articles` only iterates over seed URLs and stores newly collected ones,
while all the extraction is performed via protected `_extract_url` method.

> NOTE: at this point, an approach for extracting articles URLs is different for each website

Finally, to access seed URLs of the crawler, `get_search_urls` must be employed.

> It is possible that at some point your crawler will encounter an unavailable website (e.g. its response code is not 200).
> In such case, your crawler must continue processing the other URLs provided. 
> Ensure that your crawler handles such URLs without throwing an exception.

##### What if my web source expects a user to scroll to provide more URLs?

In that case, it is suggested to use [`selenium` library](https://www.selenium.dev/) as it allows to automatically imitate user actions. 

> HINT: follow [official instruction](https://www.selenium.dev/documentation/webdriver/getting_started/install_drivers/) to install Chrome driver.


To do that, instantiate [`selenium.webdriver.Chrome`](https://www.selenium.dev/documentation/webdriver/browsers/chrome/) class. It emulates a native browsing. Save the Chrome instance to the `driver` attribute of a Crawler.

> HINT: to disable a browser window pop-up, add `headless` mode argument to the `selenium.webdriver.chrome.options.Options` instance. Pass the instance to the `Chrome` initialization method. Make sure to only do it when the corresponding field in the crawler configuration requires it. 

Next, to open the page, use `driver.get` method.

Example usage:

```py
self.driver.get(base_url=https://github.com/)
```

To perform scroll, execute the corresponding script:

```py
 self.driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
```

To extract resulting page HTML, refer to the driver's `page_source` attribute.

##### What if my web source requires a user to click buttons to provide more URLs?

In that case, you should take the following steps. Firstly, it is necessary to find the clickable buttons with `driver.find_elements` methods.
Use [documentation](https://www.selenium.dev/documentation/webdriver/elements/finders/) to determine the arguments to be passed to find the desired elements.  Usually the elements corresponding to buttons possess `click` method. In some cases it is necessary to emulate key pressing. To do this, refer to `button.send_keys` method. 

> HINT: to find the `send_keys` argument that corresponds to the desired key, refer [here](https://github.com/SeleniumHQ/selenium/blob/selenium-4.2.0/py/selenium/webdriver/common/keys.py#L23).

Example usage:

```py
button = [button for button in self.driver.find_elements(
          by=By.TAG_NAME, value="button") if button.text == "Ещё"][0]
button.send_keys(Keys.RETURN)
```

Sometimes it is necessary to wait until the button becomes clickable. To perform this via `selenuim`, refer to `selenium.webdriver.support.wait.WebDriverWait` and `selenium.webdriver.support.expected_conditions`.

Example usage:

```py
button = WebDriverWait(self.driver, 10).until(expected_conditions.element_to_be_clickable(button))
```

### Stage 4. Extract data from every article page

#### Stage 4.1 Introduce `HTMLParser` abstraction

`HTMLParser` is an entity that is responsible for extraction of all needed information
from a single article web page. Parser is initialized the following way:

```py
parser = HTMLParser(article_url=full_url, article_id=i, config=configuration)
```

`HTMLParser` instance saves all constructor arguments in attributes with
corresponding names. Each instance should also have an
additional attribute `self.article`, initialized with a new instance of Article class.

Article is an abstraction that is implemented for you. You must use it in your
implementation. A more detailed description of the Article class can be found
[here](../docs/public/article.md). 

#### Stage 4.2 Implement main `HTMLParser` method

`HTMLParser` interface includes a single method `parse` that encapsulates the logic
of extracting all necessary data from the article web page. It should do the following:

1. download the web page;
1. initialize `BeautifulSoup` object on top of downloaded page (we will call it `article_bs`);
1. fill Article instance by calling private methods to extract text 
   (more details in the next sections).

`parse` method usage is straightforward:
```py
article = parser.parse()
```

As you can see, `parse` method returns the instance of `Article` that is stored in 
`self.article` field.

#### Stage 4.3 Implement extraction of text from article page

Extraction of the text should happen in the private `HTMLParser` method
`_fill_article_with_text`:

```py
def _fill_article_with_text(self, article_bs):
   pass
```

> NOTE: a method receives a single argument `article_bs`, which is an instance of 
> `BeautifulSoup` object, and returns `None`

A call to this method results in filling the internal Article instance with text.

> NOTE: it is very likely that the text on pages of a chosen website is split across different
> HTML blocks, make sure to collect text from them all.
### Stage 5. Save article (Stages 0-4 are required to get the mark 4)

Make sure that you save each `Article` object as a text file on the file system by
using the appropriate API method `to_raw` from [IO module](](../docs/public/article.md):

```py
to_raw(article)
```

As we return the `Article` instance from the `parse` method, saving the article is out of
scope of an `HTMLParser`. This means that you need to save the articles in the place where you
call `HTMLParser.parse()`.

### Stage 6. Collect basic article metadata (Stages 0-5 are required to get the mark 6)

According to the [dataset definition](../docs/public/dataset.md), the dataset that is generated by your code
should contain meta-information about each article including its id, title, author.

You should extend `HTMLParser` with a method `_fill_article_with_meta_information`:

```py
def _fill_article_with_meta_information(self, article_bs):
   pass
```

> NOTE: method receives a single argument `article_bs` which is an instance of 
> `BeautifulSoup` object and returns `None`

A call to this method results in filling the internal Article instance with meta-information.

> NOTE: authors must be saved as a list of strings.
> NOTE: if there is no author in your newspaper, fill the field with a list with a single string "NOT FOUND".

To save the collected meta-information, refer to IO module method `to_meta`:

```py
to_meta(article)
```

Saving the meta-information must be performed outside of parser methods.

### Stage 7. Collect advanced metadata: publication date and topics

There is plenty of information that can be collected from each page, much more than title and
author. It is very common to also collect publication date. Working with dates often becomes
a nightmare for a data scientist. It can be represented very differently: `2009Feb17`, 
`2009/02/17`, `20130623T13:22-0500`, or even `48/2009` (do you understand what 48 stand for?). 

The task is to ensure that each article metadata is extended with dates. However, the task is
even harder as you have to follow the required format. In particular, you need to translate 
it to the format shown by example: `2021-01-26 07:30:00`. 
For example, in [this paper](https://www.nn.ru/text/realty/2021/01/26/69724161/) it is stated that 
the article was published at `26 ЯНВАРЯ 2021, 07:30`, but in the meta-information it must 
be written as`2021-01-26 07:30:00`.

> HINT: use [`datetime`](https://docs.python.org/3/library/datetime.html) module for such 
> manipulations. In particular, you need to parse the date from your website that is represented 
> as a string and transform it to the instance of `datetime`. For that it might be useful
> to look into [`datetime.datetime.strptime()`](https://docs.python.org/3/library/datetime.html#strftime-strptime-behavior)
> method.

> HINT #2: inspect Article class for any date transformations

Except for that, you are also expected to extract information about topics, or 
keywords, which relate to the article you are parsing. You are expected to store
them in a meta-information file as a list-like value for the key `topics`.
In case there are not any topics or keywords present in your source,
leave this list empty. 

You should extend `HTMLParser` method `_fill_article_with_meta_information`
with date manipulations and topics extraction.

### Stage 8. Determine the optimal number of seed URLs (Stages 0-7 are required to get the mark 8)

As it was stated in Stage 2.1, "Crawler is an entity that visits `seed_urls` with the 
intention to collect URLs with articles that should be parsed later." Often you can
reach the situation when there are not enough article links on the given URL. For example,
you may want to collect 100 articles whereas each newspaper page contains links to only 10 articles. 
This brings the need in at least 10 seed URLs to be used for crawling. At this stage
you need to ensure that your Crawler is able to find and parse the required number of articles. 
Do this by determining exactly how many seed URLs it takes.

As before, such settings are specified in the config file.

> IMPORTANT: ensure you have enough seeds in your configuration file to get at least 100 
> articles in your dataset. 100 is a required number of papers for the final part of the
> course.

### Stage 9. Turn your crawler into a real recursive crawler (Stages 0-9 are required to get the mark 10)

Crawlers used in production or even just for collection of documents from a website should be 
much more robust and tricky than what you have implemented during the previous steps. To name
a few challenges:

1. Content is not in HTML. Yes, it can happen that your website is an empty HTML by default and content appears 
   dynamically when you click, scroll, etc. For example, many pages have so-called virtual scroll, it is when new 
   content appears when you scroll the page. You can think of feed in VKontakte, for example.
1. The website's defense against your crawler. Even if data is public, your crawler that sends thousands of requests 
   produces huge load on the server and exposes risks for business continuity. Therefore, websites may 
   reject too much traffic of suspicious origins.
1. There may be no way to specify seed URLs - due to website size or budget constraints. Imagine you need to 
   collect 100k articles of the Wikipedia. Do you think you would be able to copy-paste enough seeds? How 
   about the task of collection 1M articles?
1. Software and hardware limitations and accidents. Imagine you have your crawler running for 24 hours, and 
   it crashes. If you have not mitigated this risk, you lose everything and have to restart your crawler.  

And we are not talking about such objective challenges as impossibility of building universal
crawlers.

Therefore, your Stage 8 is about addressing some of these questions. In particular, you need to 
implement your crawler in a recursive manner: you provide a single seed url of your newspaper, and it
visits every page of the website and collects *all* articles from the website. You need to
make a child of `Crawler` class and name it `CrawlerRecursive`. Follow the interface of Crawler.

A required addition is an ability to stop crawler at any time. When it is started again, it
continues search and crawling process without repetitions. 

> HINT: think of storing intermediate information in one or few files? What information do you
> need to store?


#### Stage 9.1 Introduce `CrawlerResursive` abstraction

`CrawlerResursive` must inherit from `Crawler`. The initialization interface is the same as for `Crawler`. During initialization, make sure to create a field for `start_url`: it is a single URL that will be used as a seed. Fill `start_url` with one of the seed URLs presented in the configuration instance.

Interface to implement:

```py
class CrawlerRecursive(Crawler):

    def __init__(self, config: Config) -> None:
        pass
```

#### Stage 9.2 Re-implement `find_articles` method

The key idea of recursive crawling is collecting a required number of URLs (however large it may be) given just one seed URL. It can be achieved in the following way. Firstly, extract all the available URLs from the seed URL provided. If the number of extracted URLs is smaller than the required number, extract all the available URLs from the URLs that were extracted during the previous step. Repeat this process until the desired number of URLs is found. 

> HINT: `find_articles` must be called inside the `find_articles`.

Interface to implement:

```py
def find_articles(self) -> None:
    pass
```
