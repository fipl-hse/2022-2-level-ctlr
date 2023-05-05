"""
Crawler implementation
"""
import datetime
import json
import re
import shutil
from pathlib import Path
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (ASSETS_PATH, CRAWLER_CONFIG_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT,
                                  TIMEOUT_UPPER_LIMIT, TIMEOUT_LOWER_LIMIT)


class IncorrectSeedURLError (Exception):
    """
    Thrown when seed URL does not match standard pattern
    """


class NumberOfArticlesOutOfRangeError (Exception):
    """
    Thrown when total number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError (Exception):
    """
    Thrown when total number of articles to parse is not integer
    """


class IncorrectHeadersError (Exception):
    """
    Thrown when headers are not in a form of dictionary
    """


class IncorrectEncodingError (Exception):
    """
    Thrown when encoding is not specified as a string
    """


class IncorrectTimeoutError (Exception):
    """
    Thrown when timeout value is not a positive integer less than 60
    """


class IncorrectVerifyError (Exception):
    """
    Thrown when verify certificate value is neither True nor False
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
        self._validate_config_content()
        config = self._extract_config_content()

        self._seed_urls = config.seed_urls
        self._num_articles = config.total_articles
        self._headers = config.headers
        self._encoding = config.encoding
        self._timeout = config.timeout
        self._should_verify_certificate = config.should_verify_certificate
        self._headless_mode = config.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return ConfigDTO(**config)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config = self._extract_config_content()

        if not isinstance(config.seed_urls, list) or not config.seed_urls:
            raise IncorrectSeedURLError('Seed URLs is not a list')
        for url in config.seed_urls:
            if not isinstance(url, str):
                raise IncorrectSeedURLError('Seed URL is not a string')
            if not re.match(r"https?://w?w?w?.", url):
                raise IncorrectSeedURLError('Seed URL does not match standard pattern')

        if not isinstance(config.total_articles, int):
            raise IncorrectNumberOfArticlesError('Total number of articles is not integer')

        if config.total_articles > NUM_ARTICLES_UPPER_LIMIT or config.total_articles < 1:
            raise NumberOfArticlesOutOfRangeError('Total number of articles is out of range')

        if not isinstance(config.headers, dict):
            raise IncorrectHeadersError('Headers are not in dictionary form')

        if not isinstance(config.encoding, str):
            raise IncorrectEncodingError('Encoding is not a string')

        if not isinstance(config.timeout, int):
            raise IncorrectTimeoutError('Timeout value is not an integer')
        if not TIMEOUT_LOWER_LIMIT <= config.timeout <= TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError('Timeout value is out of range')

        if not isinstance(config.headless_mode, bool) or not isinstance(config.should_verify_certificate, bool):
            raise IncorrectVerifyError('Verify certificate value is not boolean')

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
        self.config = config
        self.seed_urls = config.get_seed_urls()
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if isinstance(url, str):
            return 'https://vz-nn.ru' + url
        return 'not found'

    def find_articles(self) -> None:
        """
        Finds articles
        """
        seed_urls = self.get_search_urls()
        for seed_url in self.seed_urls:
            response = make_request(seed_url, self.config)
            if response.status_code != 200:
                continue
            main_bs = BeautifulSoup(response.text, 'lxml')
            articles = main_bs.find_all('div', {'class': 'news-item'})
            for article_bs in articles:
                if len(self.urls) >= self.config.get_num_articles():
                    return
                url = self._extract_url(article_bs.find('a'))
                if url not in self.urls:
                    url_response = make_request(url, self.config)
                    if url_response.status_code != 200:
                        continue
                    self.urls.append(url)

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self.seed_urls


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
        main_bs = article_soup.find('div', {'class': 'item'})
        content = main_bs.findAll('p')
        if content:
            for paragraph in content:
                self.article.text += paragraph.text

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        pass

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        pass


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
    prepare_environment(ASSETS_PATH)

    config = Config(path_to_config=CRAWLER_CONFIG_PATH)
    crawler = Crawler(config=config)

    crawler.find_articles()
    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=i, config=config)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)


if __name__ == "__main__":
    main()
