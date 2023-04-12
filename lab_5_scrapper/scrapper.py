"""
Crawler implementation
"""
import datetime
import json
import re
from pathlib import Path
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.config_dto import ConfigDTO
from core_utils.constants import CRAWLER_CONFIG_PATH


class IncorrectSeedURLError(Exception):
    """
    Incorrect seed URl
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Number Of Articles Out Of Range
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Incorrect Number Of Articles Error
    """


class IncorrectHeadersError(Exception):
    """
    Incorrect Headers Error
    """


class IncorrectEncodingError(Exception):
    """
    Incorrect Encoding Error
    """


class IncorrectTimeoutError(Exception):
    """
    Incorrect Timeout Error
    """


class IncorrectVerifyError(Exception):
    """
    Incorrect Verify Error
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
        self._extract_config_content()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, "r") as f:
            loaded = json.load(f)
        return ConfigDTO(**loaded)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        configdto = self._extract_config_content()
        if not isinstance(configdto.seed_urls, list):
            raise IncorrectSeedURLError
        for seedurl in configdto.seed_urls:
            if not re.match(r"https?://w?w?w?.", seedurl):
                raise IncorrectSeedURLError

        if not isinstance(configdto.total_articles, int):
            raise IncorrectNumberOfArticlesError

        if configdto.total_articles < 1 or configdto.total_articles > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(configdto.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(configdto.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(configdto.timeout, int) or configdto.timeout < 0 or configdto.timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(configdto.verify_certificate, bool) or not isinstance(configdto.headless_mode, bool):
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        pass

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        pass

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        pass

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        pass

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        pass

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        pass

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        pass


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
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)


if __name__ == "__main__":
    main()
