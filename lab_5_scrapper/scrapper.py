"""
Crawler implementation
"""
from typing import Pattern, Union
import json
import re
from core_utils.config_dto import ConfigDTO
from core_utils.article.article import Article
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import time
import datetime


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
        self.config_dto = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = self.config_dto.seed_urls
        self._headers = self.config_dto.headers
        self._num_articles = self.config_dto.total_articles
        self._get_encoding = self.config_dto.encoding
        self._timeout = self.config_dto.timeout
        self._should_verify_certificate = self.config_dto.should_verify_certificate
        self._headless_mode = self.config_dto.headless_mode

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
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            parameters = json.load(f)

        for url in parameters['seed_urls']:
            if not re.match(r'https?://w?w?w?.', url) or not url.startswith('https://piter.tv/event/'):
                raise IncorrectSeedURLError

        if parameters['total_articles_to_find_and_parse'] not in range(1, 150):
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(parameters['total_articles_to_find_and_parse'], int):
            raise IncorrectNumberOfArticlesError

        if not isinstance(parameters['headers'], dict):
            raise IncorrectHeadersError

        if not isinstance(parameters['encoding'], str):
            raise IncorrectEncodingError

        if parameters['timeout'] > 60 or parameters['timeout'] < 0:
            raise IncorrectTimeoutError

        #if not isinstance(parameters[''])
            #raise IncorrectVerifyError

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
        return self._get_encoding

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
        pass


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    time.sleep(8)
    return requests.get(url,
                        headers=config.get_headers(),
                        timeout=config.get_timeout()
                        )


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
        self._seed_urls = config.get_seed_urls()
        self._config = config

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        href = article_bs.get('href')
        if href.startswith('https://piter.tv/event/'):
            return href

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self._seed_urls:
            response = requests.get(url, self._config)
            main_bs = BeautifulSoup(response.text, 'lxml')
            for element in main_bs.find_all('a', {'class':'news-article_link'}):
                if len(self.urls) < self._config.get_num_articles():
                    self.urls.append('https://piter.tv/news/' + self._extract_url(element))

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
        self.article = Article(self.full_url, self.article_id)

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
