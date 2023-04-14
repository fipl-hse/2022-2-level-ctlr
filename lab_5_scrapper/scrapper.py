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


class IncorrectSeedURLError(TypeError):
    """
    seed URL does not match standard pattern
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    total number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    total number of articles to parse is not integer
    """


class IncorrectHeadersError(Exception):
    """
    headers are not in a form of dictionary
    """


class IncorrectEncodingError(Exception):
    """
    encoding must be specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    timeout value must be a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
     verify certificate value must either be True or False
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

        if not isinstance(config.seed_urls, list):
            raise IncorrectSeedURLError('seed URL is not a list')

        for url in config.seed_urls:
            if not re.match(r'^https?://.*', url):
                raise IncorrectSeedURLError

        if (not isinstance(config.total_articles, int)
                or isinstance(config.total_articles, bool)
                or config.total_articles <= 0):
            raise IncorrectNumberOfArticlesError

        if config.total_articles > NUM_ARTICLES_UPPER_LIMIT \
                or config.total_articles < 1:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(config.timeout, int) or \
                not TIMEOUT_LOWER_LIMIT <= config.timeout <= TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        if not isinstance(config.should_verify_certificate, bool):
            raise IncorrectVerifyError

        if not isinstance(config.headless_mode, bool):
            raise IncorrectVerifyError()

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
    time.sleep(random.randint(1, 3))
    timeout = config.get_timeout()
    headers = config.get_headers()

    response = requests.get(url, timeout=timeout, headers=headers)
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
        self._seed_url = config.get_seed_urls()
        self._config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        return str(article_bs)

    def find_articles(self) -> None:
        """
        Finds articles
        """
        url1 = "https://prmira.ru"
        for url in self._seed_url:
            response = make_request(url, self._config)
            file = response.json()
            for values in file.values():
                for elem in values:
                    if isinstance(elem, dict):
                        if len(self.urls) >= self._config.get_num_articles():
                            return
                        link = url1 + elem['path']
                        if not link or link in self.urls:
                            continue
                        self.urls.append(url1 + elem['path'])

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._seed_url


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
        first = article_soup.find("div",
                                  class_='text-[16px] leading-relaxed '
                                         'font-semibold mb-8 lg:font-sans '
                                         'lg:text-[28px] lg:leading-[1.35] lg:mb-[16px]')

        elements = (article_soup.find_all("div",
                                          class_=['mb-[24px] lg:mb-[28px]',
                                                  'Common_common__MfItd']))
        paraghaph = []
        self.article.text += first.text
        for elem in elements:
            par = elem.find_all(['p', 'blockquote'])
            for elem in par:
                paraghaph.append(elem.text)

        self.article.text += " ".join(paraghaph)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        author = article_soup.find('a',
                                   {'class': 'inline-block text-[11px] mr-1 mb-1 text-[#276FFF]'})
        self.article.author = [author.text[1:] if author else "NOT FOUND"]

        title = article_soup.find('h1')
        self.article.title = title.text

        topics = article_soup.find_all \
            ('a', {'class': 'inline-block text-[11px] mr-1 mb-1 text-[#276FFF]'})
        if topics[1:]:
            for topic in topics[1:]:
                self.article.topics.append(topic.text[1:])

        date = article_soup.find('div', {'class': 'MatterTop_date__NIUrJ'})
        date_str = date.text if date else "NOT FOUND"
        self.article.date = self.unify_date_format(date_str)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        months_dict = {
            "января": "01",
            "февраля": "02",
            "марта": "03",
            "апреля": "04",
            "мая": "05",
            "июня": "06",
            "июля": "07",
            "августа": "08",
            "сентября": "09",
            "октября": "10",
            "ноября": "11",
            "декабря": "12"
        }
        date_str = date_str.replace(date_str.split()[1], months_dict[date_str.split()[1]])
        return datetime.datetime.strptime(date_str, '%d %m %Y, %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        article = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article)
        self._fill_article_with_meta_information(article)
        return self.article


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
    config = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=config)
    crawler.find_articles()
    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=i, config=config)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
