"""
Crawler implementation
"""
import datetime
from pathlib import Path
from typing import Pattern, Union
import json

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.config_dto import ConfigDTO

import core_utils.constants as const


class IncorrectSeedURLError(Exception):
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    pass


class IncorrectNumberOfArticlesError(Exception):
    pass


class IncorrectHeadersError(Exception):
    pass


class IncorrectEncodingError(Exception):
    pass


class IncorrectTimeoutError(Exception):
    pass


class IncorrectVerifyError(Exception):
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
        self.config_dto = self._extract_config_content()
        self._validate_config_content()
        self._get_seed_urls = self.get_seed_urls()
        self._num_articles = self.get_num_articles()
        self._get_headers = self.get_headers()
        self._get_encoding = self.get_encoding()
        self._get_timeout = self.get_timeout()
        self._verify_certificate = self.get_verify_certificate()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as infile:
            reader = json.load(infile)
        return ConfigDTO(**reader)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        if not self.config_dto.seed_urls or not isinstance(self.config_dto.seed_urls, list) \
                or not all(isinstance(url, str) for url in self.config_dto.seed_urls):
            raise IncorrectSeedURLError

        if not isinstance(self.config_dto.total_articles_to_find_and_parse, int) \
                or not 1 < self.config_dto.total_articles_to_find_and_parse < 150:
            raise IncorrectNumberOfArticlesError

        if not self.config_dto.seed_urls and not isinstance(self.config_dto.headers, dict) \
                and not all(isinstance(key, str) and isinstance(value, str)
                            for key, value in self.config_dto.headers.items()):
            raise IncorrectHeadersError

        if not isinstance(self.config_dto.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(self.config_dto.timeout, int) or self.config_dto.timeout < 1 or self.config_dto.timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(self.config_dto.verify_certificate, bool):
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.config_dto.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.config_dto.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.config_dto.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.config_dto.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.config_dto.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.config_dto.verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.config_dto.headless_mode


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
    config = Config(const.CRAWLER_CONFIG_PATH)


if __name__ == "__main__":
    main()
