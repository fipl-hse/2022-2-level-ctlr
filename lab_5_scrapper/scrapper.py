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
    Seed URL does not match standard pattern "https?://(www.)?".
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is more than the maximum of 150
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
    Encoding is not a string
    """


class IncorrectTimeoutError(Exception):
    """
    Timeout value is not a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    Verify certificate value is not boolean
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
        self.config = self._extract_config_content()

        self._seed_urls = self.config.seed_urls
        self._num_articles = self.config.total_articles
        self._headers = self.config.headers
        self._encoding = self.config.encoding
        self._timeout = self.config.timeout
        self._should_verify_certificate = self.config.should_verify_certificate
        self._headless_mode = self.config.headless_mode

        self._validate_config_content()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as config:
            f = json.load(config)
        return ConfigDTO(**f)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        if not isinstance(self._seed_urls, list)\
                or not all(isinstance(url, str) for url in self._seed_urls) or \
                not all(re.search('https?://(www.)?', url) for url in self._seed_urls):
            raise IncorrectSeedURLError
        if not isinstance(self._num_articles, int) or self._num_articles < 1:
            raise IncorrectNumberOfArticlesError
        if self._num_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError
        if not isinstance(self._headers, dict):
            raise IncorrectHeadersError
        if not isinstance(self._encoding, str):
            raise IncorrectEncodingError
        if not isinstance(self._timeout, int)\
                or self._timeout <= TIMEOUT_LOWER_LIMIT or self._timeout >= TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError
        if not isinstance(self._should_verify_certificate, bool)\
                or not isinstance(self._headless_mode, bool):
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
    random_timeout = random.randint(1, 10) / 10
    time.sleep(random_timeout)
    response = requests.get(url, headers=config.get_headers(),
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
        self.config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        if isinstance(href := article_bs.get('href'), str):
            return 'https://ptzgovorit.ru' + href
        return 'mypy shut up'

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self.get_search_urls():
            while True:
                req = make_request(seed_url, self.config)
                page_bs = BeautifulSoup(req.text, 'lxml')
                if page_bs.find('section', {'id': 'block-views-main-block-1'}):
                    break
            for a_href in page_bs.find_all('a', href=lambda href: isinstance(href, str)):
                if len(self.urls) >= self.config.get_num_articles():
                    return
                url = self._extract_url(a_href)
                if url not in self.urls and url.startswith('https://ptzgovorit.ru/news/'):
                    self.urls.append(url)

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
        text_div = article_soup.find('div', {'class': 'field-type-text-with-summary'})
        self.article.text = '\n'.join(text for paragraph in text_div.find_all('p')
                                      if (text := paragraph.text.strip()))

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h2', {'class': 'node-title'})
        self.article.title = title.text
        date = article_soup.find('div', {'class': 'node-date'})
        self.article.date = self.unify_date_format(date.text)

        text_div = article_soup.find('div', {'class': 'field-type-text-with-summary'})
        if author := text_div.find_all(string=re.compile('^Текст: ')):
            self.article.author = [' '.join(author[0].text.split()[1:3])]
        elif author := text_div.find_all(string=re.compile('^Текст и фото: ')):
            self.article.author = [' '.join(author[0].text.split()[3:5])]
        else:
            self.article.author = ['NOT FOUND']

        topic_list = []
        topics = article_soup.find('div', {'class': 'field-name-field-tags'}).find_all('a')
        for url in topics:
            topic_list.append(url.text)
        self.article.topics = topic_list

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        months_substitutions = {'декабря': 'Dec', 'января': 'Jan', 'февраля': 'Feb',
                                'марта': 'Mar', 'апреля': 'Apr', 'мая': 'May',
                                'июня': 'Jun', 'июля': 'Jul', 'августа': 'Aug',
                                'сентября': 'Sep', 'октября': 'Oct', 'ноября': 'Nov', }
        date = date_str.split()
        date[1] = months_substitutions[date[1]]
        return datetime.datetime.strptime(' '.join(date), '%d %b %Y, %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        while True:
            req = make_request(self.full_url, self.config)
            article_bs = BeautifulSoup(req.text, 'lxml')
            self._fill_article_with_text(article_bs)
            if not self.article.text:
                continue
            self._fill_article_with_meta_information(article_bs)
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
    prepare_environment(ASSETS_PATH)
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, article_url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=article_url, article_id=i, config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
