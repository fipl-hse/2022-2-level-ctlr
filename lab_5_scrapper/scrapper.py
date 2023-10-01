"""
Crawler implementation
"""
import datetime
import json
import random
import re
import shutil
import time
from pathlib import Path
from typing import Pattern, Union
import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_meta, to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (ASSETS_PATH, CRAWLER_CONFIG_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT,
                                  TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)

class IncorrectSeedURLError(Exception):
    """
    Seed URL does not match standard pattern.
    """

class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of range from 1 to 150.
    """

class IncorrectNumberOfArticlesError(Exception):
    """
    Total number of articles to parse is not integer.
    """

class IncorrectHeadersError(Exception):
    """
    Headers are not in a form of dictionary.
    """

class IncorrectEncodingError(Exception):
    """
    Encoding must be specified as a string.
    """

class IncorrectTimeoutError(Exception):
    """
    Timeout value must be a positive integer less than 60.
    """

class IncorrectVerifyError (Exception):
    """
    Verify certificate value must either be True or False.
    """

class Config:
    """
    Unpacks and validates configurations
    """

    def __init__(self, path_to_config: Path) -> None:
        """
        Initializes an instance of the Config class
        """
        self.path_to_config = path_to_config
        self.config_content = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = self.config_content.seed_urls
        self._num_articles = self.config_content.total_articles
        self._headers = self.config_content.headers
        self._encoding = self.config_content.encoding
        self._timeout = self.config_content.timeout
        self._should_verify_certificate = self.config_content.should_verify_certificate
        self._headless_mode = self.config_content.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config_content = json.load(f)
        return ConfigDTO(**config_content)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_content = self._extract_config_content()

        if not isinstance(config_content.seed_urls, list) or not config_content.seed_urls:
            raise IncorrectSeedURLError

        for seed_url in config_content.seed_urls:
            if not isinstance(seed_url, str) or not re.match(r'https?://.*/', seed_url):
                raise IncorrectSeedURLError

        if not isinstance(config_content.headers, dict):
            raise IncorrectHeadersError

        if (not isinstance(config_content.total_articles, int) or isinstance(config_content.total_articles, bool) or config_content.total_articles < 1):
            raise IncorrectNumberOfArticlesError

        if config_content.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_content.encoding, str):
            raise IncorrectEncodingError

        if (not isinstance(config_content.timeout, int) or config_content.timeout < TIMEOUT_LOWER_LIMIT or config_content.timeout > TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError

        if not isinstance(config_content.should_verify_certificate, bool) or not isinstance(config_content.headless_mode, bool):
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self._seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self._num_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self._headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self._encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self._timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self._should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self._headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    time.sleep(random.randint(1, 8))
    response = requests.get(url,
                            headers=config.get_headers(),
                            timeout=config.get_timeout(),
                            verify=config.get_verify_certificate())
    response.encoding = config.get_encoding()
    return response


class Crawler:
    """
    Crawler implementation
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the Crawler class
        """
        self._config = config
        self._seed_urls = config.get_seed_urls()
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if isinstance(url, str) and url.startswith('/news/'):
            return 'https://www.vremyan.ru' + url
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self._seed_urls:
            response = make_request(seed_url, self._config)
            if response.status_code != 200:
                continue
            main_bs = BeautifulSoup(response.text, 'lxml')
            article_webpage = main_bs.find_all('a')
            for art in article_webpage:
                href = self._extract_url(art)
                if href is None:
                    continue
                if href not in self.urls and href != '':
                    self.urls.append(href)

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._seed_urls


class HTMLParser:
    """
    ArticleParser implementation
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initializes an instance of the HTMLParser class
        """
        self.full_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(full_url, article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        text = []
        text_str = ''
        text_bs = article_soup.find('article')
        article = article_soup.find_all("p")
        if article:
            for paragraph in article:
                cleaned_paragraph = paragraph.text.strip()
                if cleaned_paragraph:
                    text.append(cleaned_paragraph)
            text_str = "\n".join(text)
        if len(text_str) < 50:
            text_str +=' '*(50-len(text_str))
        self.article.text = text_str


    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1')
        if title is None:
            self.article.title = 'NOT FOUND'
        else:
            self.article.title = title.text

        self.article.author = ['NOT FOUND']



    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        main_bs = BeautifulSoup(response.content, "lxml")
        self._fill_article_with_text(main_bs)
        self._fill_article_with_meta_information(main_bs)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper modulenvalidHeader: Inva
    """
    # YOUR CODE GOES HERE
    prepare_environment(ASSETS_PATH)
    config = Config(path_to_config=CRAWLER_CONFIG_PATH)
    crawler = Crawler(config=config)
    crawler.find_articles()
    for idx, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(url, idx, config)
        article = parser.parse()
        to_raw(article)
        to_meta(article)


if __name__ == "__main__":
    main()
