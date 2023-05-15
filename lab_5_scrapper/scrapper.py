"""
Crawler implementation
"""
import datetime
import json
import os
import re
import shutil
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
    Seed URL does not match standard pattern "https?://w?w?w?."
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Total number of articles to parse is not integer
    """


class IncorrectHeadersError(Exception):
    """
    Headers are not in a form of dictionary
    """


class IncorrectEncodingError(Exception):
    """
    Encoding must be specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    Timeout value must be a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    Verify certificate value must either be True or False
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
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config_dto = json.load(file)
        return ConfigDTO(**config_dto)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()

        if not isinstance(config_dto.seed_urls, list):
            raise IncorrectSeedURLError(IncorrectSeedURLError.__doc__.strip())

        for url in config_dto.seed_urls:
            if not (isinstance(url, str) and re.match(r'https?://(www.)?', url)):
                raise IncorrectSeedURLError(IncorrectSeedURLError.__doc__.strip())

        if not (isinstance(config_dto.total_articles, int) and config_dto.total_articles > 0):
            raise IncorrectNumberOfArticlesError(IncorrectNumberOfArticlesError.__doc__.strip())

        if not config_dto.total_articles < NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError(NumberOfArticlesOutOfRangeError.__doc__.strip())

        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError(IncorrectHeadersError.__doc__.strip())

        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError(IncorrectEncodingError.__doc__.strip())

        if not (isinstance(config_dto.timeout, int) and
                TIMEOUT_LOWER_LIMIT < config_dto.timeout <= TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError(IncorrectTimeoutError.__doc__.strip())

        if not (isinstance(config_dto.should_verify_certificate, bool) and
                isinstance(config_dto.headless_mode, bool)):
            raise IncorrectVerifyError(IncorrectVerifyError.__doc__.strip())

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
    return requests.get(url=url,
                        headers=config.get_headers(),
                        timeout=config.get_timeout(),
                        verify=config.get_verify_certificate())


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
        main_href = 'https://www.kommersant.ru'
        article_href = article_bs.get('href')
        if isinstance(article_href, str) and article_href.startswith('/doc/'):
            return main_href + article_href
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url_to_crawl in self.get_search_urls():
            response = make_request(url_to_crawl, self.config)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'lxml')
                articles_html = soup.find_all('a', class_='uho__link uho__link--overlay')

                for article in articles_html:
                    result_url = self._extract_url(article)
                    if result_url and result_url not in self.urls:
                        self.urls.append(result_url)

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
        self.article = Article(full_url, article_id)
        self.full_url = full_url
        self.article_id = article_id
        self.config = config

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        unformatted_text = article_soup.find('article').find_all('p', class_='doc__text')
        self.article.text = ' '.join(paragraph.text for paragraph in unformatted_text[:-1])

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1', class_='doc_header__name js-search-mark').text.strip()
        self.article.title = title

        author = article_soup.find('p', class_='doc__text document_authors')
        self.article.author = list(author) if author else ["NOT FOUND"]

        topics = list(theme.text for theme in
                      article_soup.find_all('a', class_='doc_footer__item_name'))
        self.article.topics = topics

        date = article_soup.find('div', class_='doc_header__time').find('time').attrs['datetime']
        self.article.date = self.unify_date_format(date)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S+03:00')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        article_bs = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article_bs)
        self._fill_article_with_meta_information(article_bs)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if os.path.exists(base_path):
        shutil.rmtree(base_path)
    os.makedirs(base_path)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    prepare_environment(ASSETS_PATH)
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)

    crawler = Crawler(config=configuration)
    crawler.find_articles()

    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(url, i, configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
