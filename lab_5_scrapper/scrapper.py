"""
Crawler implementation
"""
from typing import Pattern, Union
from pathlib import Path
import json
import re
# import datetime
import requests
from bs4 import BeautifulSoup
from core_utils.config_dto import ConfigDTO
from core_utils.article.article import Article
# from core_utils.constants import (CRAWLER_CONFIG_PATH)


class IncorrectSeedURLError(Exception):
    """
    Raises when seed URL does not match standard pattern "https?://w?w?w?.
    """
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Raises when total number of articles is out of range from 1 to 150
    """
    pass


class IncorrectNumberOfArticlesError(Exception):
    """
    Raises when total number of articles to parse is not integer
    """
    pass


class IncorrectHeadersError(Exception):
    """
    Raises when total number of articles to parse is not integer
    """
    pass


class IncorrectEncodingError(Exception):
    """
    Raises when encoding does not specified as a string
    """
    pass


class IncorrectTimeoutError(Exception):
    """
    Raises when timeout value is not a positive integer less than 60
    """
    pass


class IncorrectVerifyError(Exception):
    """
    Raises when verify certificate value does not either be True or False
    """
    pass


class Config:
    """
    Unpacks and validates configurations
    """
    def __init__(self, path_to_config: Path) -> None:
        """
        Initializes an instance of the Config class
        """
        self.path_to_config = path_to_config
        self._config_data = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = self._config_data.seed_urls
        self._num_articles = self._config_data.total_articles_to_find_and_parse
        self._headers = self._config_data.headers
        self._encoding = self._config_data.encoding
        self._timeout = self._config_data.timeout
        self._verify_certificate = self._config_data.should_verify_certificate
        self._headless_mode = self._config_data.headless_mode

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
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            content = json.load(f)

        seed_urls = content['seed_urls']
        headers = content['headers']
        total_articles_to_find_and_parse = content['total_articles_to_find_and_parse']
        encoding = content['encoding']
        timeout = content['timeout']
        should_verify_certificate = content['should_verify_certificate']

        if not isinstance(seed_urls, list)\
                or not not all(isinstance(url, str) for url in seed_urls)\
                or not all(re.match('https?://w?w?w?.', url) for url in seed_urls):
            raise IncorrectSeedURLError

        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        if not isinstance(total_articles_to_find_and_parse, int):
            raise IncorrectNumberOfArticlesError

        if total_articles_to_find_and_parse not in range(1, 151):
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(timeout, int) or not timeout < 60 or not timeout > 0:
            raise IncorrectTimeoutError

        if not isinstance(should_verify_certificate, bool):
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
        return self.get_verify_certificate()

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.get_headless_mode()


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    pass


class Crawler:
    """
    Crawler implementation
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the Crawler class
        """
        pass

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        pass

    def find_articles(self) -> None:
        """
        Finds articles
        """
        pass

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        pass


class HTMLParser:
    """
    ArticleParser implementation
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initializes an instance of the HTMLParser class
        """
        pass

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        pass

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
    pass


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    pass


if __name__ == "__main__":
    main()
