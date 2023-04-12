"""
Crawler implementation
"""
import json
#import os.path
import re
import random
from typing import Pattern, Union
import time
from core_utils.config_dto import ConfigDTO
#from core_utils.constants import CRAWLER_CONFIG_PATH, ASSETS_PATH
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import datetime
from core_utils.article.article import Article
#from core_utils.article.io import to_raw
#import shutil


class IncorrectSeedURLError(Exception):
    """
    Seed URL does not match standard pattern "https?://w?w?w?." or does not correspond to the target website
    """
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of range from 1 to 150
    """
    pass


class IncorrectNumberOfArticlesError(Exception):
    """
    Total number of articles to parse is not integer
    """
    pass


class IncorrectHeadersError(Exception):
    """
    Headers are not in a form of dictionary
    """
    pass


class IncorrectEncodingError(Exception):
    """
    Encoding must be specified as a string
    """
    pass


class IncorrectTimeoutError(Exception):
    """
    Timeout value must be a positive integer less than 60
    """
    pass


class IncorrectVerifyError(Exception):
    """
    Verify certificate value must either be True or False
    """
    pass


class Config:
    """
    Unpacks and validates configurations
    """
    seed_urls: list[str]
    total_articles_to_find_and_parse: int
    headers: dict[str, str]
    encoding: str
    timeout: int
    verify_certificate: bool
    headless_mode: bool

    def __init__(self, path_to_config: Path) -> None:
        """
        Initializes an instance of the Config class
        """
        self.path_to_config = path_to_config
        self._validate_config_content()

        config_dto = self._extract_config_content()
        self._seed_urls = config_dto.seed_urls
        self._num_articles = config_dto.total_articles
        self._headers = config_dto.headers
        self._encoding = config_dto.encoding
        self._timeout = config_dto.timeout
        self._should_verify_certificate = config_dto.should_verify_certificate
        self._headless_mode = config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config_parameters = json.load(f)
        return ConfigDTO(**config_parameters)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_parameters = self._extract_config_content()

        if not isinstance(config_parameters.seed_urls, list):
            raise IncorrectSeedURLError

        for url in config_parameters.seed_urls:
            if not re.match("https?://.*/", url) or not isinstance(url, str):
                raise IncorrectSeedURLError

        if not isinstance(config_parameters.total_articles, int) or isinstance(config_parameters.total_articles, bool) \
                or config_parameters.total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if config_parameters.total_articles < 1 or config_parameters.total_articles > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_parameters.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config_parameters.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(config_parameters.timeout, int) or config_parameters.timeout < 0 or \
                config_parameters.timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(config_parameters.should_verify_certificate, bool) or not \
                isinstance(config_parameters.headless_mode, bool):
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
    time.sleep(random.randint(2,5))
    response = requests.get(url, headers=config.get_headers(), timeout=config.get_timeout(),
                            verify=config.get_verify_certificate())
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
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        all_links_bs = article_bs.find_all('a')
        for link_bs in all_links_bs:
            link = link_bs.get('href')
            if link is None:
                continue
            elif link[0:5] == '/news' and link.count('/') == 2:
                self.urls.append('https://tvspb.ru' + link)
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.get_search_urls():
            response = make_request(url, self.config)
            if response.status_code == 200:
                main_bs = BeautifulSoup(response.text, 'lxml')
                self._extract_url(main_bs)

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self.config.get_seed_urls()


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
        body_bs = article_soup.find_all('div', {'itemprop': 'articleBody'})[0]
        all_paragraphs = body_bs.find_all('p')
        self.article.text = all_paragraphs

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
    # YOUR CODE GOES HERE
    pass


if __name__ == "__main__":
    main()
