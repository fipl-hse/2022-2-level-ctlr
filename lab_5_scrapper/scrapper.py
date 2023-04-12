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
    Exception raised when seed_urls value in configuration
    file is not a list of strings or a string is not a valid URL
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Exception raised when total_articles_to_find_and_parse value
    in configuration file is out of range
    """


class IncorrectHeadersError(Exception):
    """
    Exception raised when headers value in configuration file is not a dictionary
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Exception raised when total_articles_to_find_and_parse
    value in configuration file is not an integer greater than 0
    """


class IncorrectEncodingError(Exception):
    """
    Exception raised when encoding value in configuration file is not a string
    """


class IncorrectTimeoutError(Exception):
    """
    Exception raised when timeout value in configuration file
    is not an integer between 1 and 30
    """


class IncorrectVerifyError(Exception):
    """
    Exception raised when should_verify_certificate
    value in configuration file is not a boolean
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
        self.content = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = self.content.seed_urls
        self._num_articles = self.content.total_articles
        self._headers = self.content.headers
        self._encoding = self.content.encoding
        self._timeout = self.content.timeout
        self._should_verify_certificate = self.content.should_verify_certificate
        self._headless_mode = self.content.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return ConfigDTO(**content)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        content = self._extract_config_content()

        seed_urls = content.seed_urls
        headers = content.headers
        total_articles_to_find_and_parse = content.total_articles
        encoding = content.encoding
        timeout = content.timeout
        should_verify_certificate = content.should_verify_certificate
        headless_mode = content.headless_mode

        if not isinstance(seed_urls, list):
            raise IncorrectSeedURLError
        for url in seed_urls:
            if not isinstance(url, str) or not re.match(r'https?://.*/', url):
                raise IncorrectSeedURLError
        if not isinstance(headers, dict):
            raise IncorrectHeadersError
        if (not isinstance(total_articles_to_find_and_parse, int)
                or isinstance(total_articles_to_find_and_parse, bool)
                or total_articles_to_find_and_parse < 1):
            raise IncorrectNumberOfArticlesError
        if total_articles_to_find_and_parse > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError
        if not isinstance(encoding, str):
            raise IncorrectEncodingError
        if (not isinstance(timeout, int)
                or timeout < TIMEOUT_LOWER_LIMIT
                or timeout > TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError
        if not isinstance(should_verify_certificate, bool) or not isinstance(headless_mode, bool):
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
    time.sleep(random.randrange(3, 7))
    headers = config.get_headers()
    timeout = config.get_timeout()
    response = requests.get(url, headers=headers, timeout=timeout)
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
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if (url is not None) and (url.startswith('/news/19'))\
                and (url.endswith('#comments') is False):
            return str(url)
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.get_search_urls():
            response = make_request(url, self._config)
            main_bs = BeautifulSoup(response.content, "lxml")
            for paragraph in main_bs.find_all('a'):
                if self._extract_url(paragraph) is not None:
                    new_url = 'https://gorod48.ru' + str(self._extract_url(paragraph))
                    self.urls.append(new_url)
                    if len(self.urls) >= self._config.get_num_articles():
                        return

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._config.get_seed_urls()


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
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        text = article_soup.find('div', class_="news-text_wrapper")
        self.article.text = "".join(text.text)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1')
        if title:
            self.article.title = title.text
        self.article.author = ["NOT FOUND"]
        data = article_soup.find('p', class_="dateElement")
        date_str = str(data.text)
        self.article.date = self.unify_date_format(date_str)
        topics = article_soup.find('div', class_="hashtagBlock").find_all('a')
        self.article.topics = [topic.text for topic in topics if topic.text != '#']

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        page = make_request(self.full_url, self.config)
        article_bs = BeautifulSoup(page.content, "lxml")
        self._fill_article_with_text(article_bs)
        self._fill_article_with_meta_information(article_bs)
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
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for index, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(url, index, configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
