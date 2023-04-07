"""
Crawler implementation
"""
from typing import Pattern, Union
from bs4 import BeautifulSoup
import requests
from core_utils.config_dto import ConfigDTO
from core_utils.article.article import Article
import json
from pathlib import Path
import time
import datetime
from requests import HTTPError
from random import randint
from core_utils.constants import CRAWLER_CONFIG_PATH, ASSETS_PATH,\
    NUM_ARTICLES_UPPER_LIMIT, TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT
import shutil
import re


class IncorrectSeedURLError(Exception):
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    pass


class IncorrectHeadersError(Exception):
    pass


class IncorrectNumberOfArticlesError(Exception):
    pass


class IncorrectEncodingError(Exception):
    pass


class IncorrectTimeoutError(Exception):
    pass


class IncorrectVerifyError(Exception):
    pass


class IncorrectHeadlessError(Exception):
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
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            content = json.load(f)

        seed_urls = content['seed_urls']
        headers = content['headers']
        total_articles_to_find_and_parse = content['total_articles_to_find_and_parse']
        encoding = content['encoding']
        timeout = content['timeout']
        should_verify_certificate = content['should_verify_certificate']
        headless_mode = content['headless_mode']

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
        return self.content.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.content.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.content.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.content.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.content.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.content.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.content.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    time.sleep(randint(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT))
    response = requests.get(url,
                            headers=config.get_headers(),
                            timeout=config.get_timeout(),
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
        self.seed_urls = config.seed_urls

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        all_links_bs = article_bs.find_all('a')
        for link_bs in all_links_bs:
            href = link_bs.get('href')
            if href is None:
                continue
            elif (href.startswith('/news/19')) and (href.count('/') == 3)\
                    and (href.endswith('#comments') is False):
                return 'https://gorod48.ru' + str(href)

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.config.get_seed_urls():
            try:
                response = make_request(url, config=self.config)
                main_bs = BeautifulSoup(response.text, 'lxml')
                new_url = self._extract_url(main_bs)
                if new_url not in self.urls:
                    self.urls.append(new_url)
            except HTTPError:
                continue

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


if __name__ == "__main__":
    main()
