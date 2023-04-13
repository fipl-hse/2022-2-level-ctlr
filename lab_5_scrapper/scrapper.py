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
    Checks seed_url format
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Checks whether total number of articles is out of range
    """


class IncorrectHeadersError(Exception):
    """
    Checks headers
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Checks number of article format
    """


class IncorrectEncodingError(Exception):
    """
    Checks encoding format
    """


class IncorrectTimeoutError(Exception):
    """
    Checks timeout format
    """


class IncorrectVerifyError(Exception):
    """
    Checks verify certificate format
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
        config_dto = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = config_dto.seed_urls
        self._headers = config_dto.headers
        self._num_articles = config_dto.total_articles
        self._encoding = config_dto.encoding
        self._timeout = config_dto.timeout
        self._should_verify_certificate = config_dto.should_verify_certificate
        self._headless_mode = config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config = json.load(file)
        return ConfigDTO(**config)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        parameters = self._extract_config_content()

        if not isinstance(parameters.seed_urls, list):
            raise IncorrectSeedURLError

        for url in parameters.seed_urls:
            if not re.match(r'https?://w?w?w?.', url) or not isinstance(url, str):
                raise IncorrectSeedURLError

        if not isinstance(parameters.total_articles, int)\
                or isinstance(parameters.total_articles, bool)\
                or parameters.total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if parameters.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(parameters.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(parameters.encoding, str):
            raise IncorrectEncodingError

        if parameters.timeout not in range(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError

        if not isinstance(parameters.should_verify_certificate, bool)\
                or not isinstance(parameters.headless_mode, bool):
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
    time.sleep(random.randint(1, 6))
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
        self.urls = []
        self._seed_urls = config.get_seed_urls()
        self._config = config

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if isinstance(url, str) and url.startswith('https://piter.tv/event/'):
            return url
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self._seed_urls:
            response = make_request(url, self._config)
            if response.status_code != 200:
                continue
            main_bs = BeautifulSoup(response.text, 'lxml')
            for one in main_bs.find_all('a', class_='news-article__link'):
                link = self._extract_url(one)
                if link is None:
                    continue
                if len(self.urls) < self._config.get_num_articles():
                    self.urls.append(link)

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
        self._full_url = full_url
        self._article_id = article_id
        self._config = config
        self.article = Article(self._full_url, self._article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        for text in article_soup.find_all('div', class_="js-mediator-article"):
            self.article.text += text.text + "\n"

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title_info = article_soup.find('h1', class_='article__title')
        title = title_info.get_text(strip=True)
        self.article.title = title

        all_authors_info = article_soup.find_all('a', class_='article__author')
        if not all_authors_info:
            self.article.author = "NOT FOUND"
        self.article.author = [author.text for author in all_authors_info]

        topics_info = article_soup.find_all('a', class_='article__tags')
        if topics_info:
            self.article.topics = [tag.text for tag in topics_info]

        date_info = article_soup.find('div', class_='article__date')
        date = date_info.find_all('#text')
        self.article.date = date


    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        page = make_request(self._full_url, self._config)
        if page.status_code == 200:
            article_bs = BeautifulSoup(page.content, 'lxml')
            self._fill_article_with_text(article_bs)
            self._fill_article_with_meta_information(article_bs)
            return self.article
        return False


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
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    crawler = Crawler(configuration)
    crawler.find_articles()
    for index, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(url, index, configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
