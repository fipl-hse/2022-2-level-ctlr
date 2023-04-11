"""
Crawler implementation
"""
import json
import re
import requests
import shutil

from typing import Pattern, Union
from datetime import datetime
from bs4 import BeautifulSoup
from core_utils.config_dto import ConfigDTO
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH, TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT
from core_utils.article.article import Article
from pathlib import Path


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
        self._validate_config_content()
        self._config_dto = self._extract_config_content()
        self._seed_urls = self._config_dto.seed_urls
        self._num_articles = self._config_dto.total_articles
        self._headers = self._config_dto.headers
        self._encoding = self._config_dto.encoding
        self._timeout = self._config_dto.timeout
        self._should_verify_certificate = self._config_dto.should_verify_certificate
        self._headless_mode = self._config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            configuration = json.load(file)
            return ConfigDTO(**configuration)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self._config_file_path, 'r', encoding='utf-8') as file:
            configuration = json.load(file)

        seed_url = configuration.get('seed_url')
        if not seed_url or not re.match(r'^https?://w?w?w?.', seed_url):
            raise IncorrectSeedURLError
        num_articles = configuration.get('num_articles')

        if not isinstance(num_articles, int):
            raise IncorrectNumberOfArticlesError

        if num_articles < 1 or num_articles > 150:
            raise NumberOfArticlesOutOfRangeError

        headers = configuration.get('headers')
        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        encoding = configuration.get('encoding')
        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        timeout = configuration.get('timeout')
        if not isinstance(timeout, int) or timeout <= TIMEOUT_LOWER_LIMIT or timeout >= TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        verify = configuration.get('verify')
        if not isinstance(verify, bool):
            raise IncorrectVerifyError



    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self._config_dto.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self._config_dto.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self._config_dto.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self._config_dto.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self._config_dto.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self._config_dto.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    headers = config.get_headers()
    timeout = config.get_timeout()
    verify = config.get_verify_certificate()
    response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    response.encoding == 'utf-8'
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
        self.urls = []
        self._config = config
        self._seed_urls = config.get_seed_urls()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """



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
    if isinstance(base_path, str):
        base_path = Path(base_path)

    if base_path.exists():
        shutil.rmtree(base_path)

    else:
        base_path.mkdir(parents=True)



def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)


if __name__ == "__main__":
    main()
