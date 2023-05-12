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
    Inappropriate value for seed url
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Number of articles either to large or small
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Inappropriate value for number of articles
    """


class IncorrectHeadersError(Exception):
    """
    Inappropriate value for headers
    """


class IncorrectEncodingError(Exception):
    """
    Inappropriate value for encoding
    """


class IncorrectTimeoutError(Exception):
    """
    Inappropriate value for timeout
    """


class IncorrectVerifyError(Exception):
    """
     Inappropriate value for certificate
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
            dict_config = json.load(file)
        return ConfigDTO(**dict_config)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()

        if not isinstance(config_dto.seed_urls, list):
            raise IncorrectSeedURLError

        for url in config_dto.seed_urls:
            if not isinstance(url, str) or \
                    not re.match(r'https://\w*.\w+.ru/\w+/*\d*', url):
                raise IncorrectSeedURLError

        if not isinstance(config_dto.total_articles, int) \
                or isinstance(config_dto.total_articles, bool) \
                or config_dto.total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if config_dto.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(config_dto.timeout, int) \
                or config_dto.timeout < TIMEOUT_LOWER_LIMIT \
                or config_dto.timeout > TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        if not (isinstance(config_dto.should_verify_certificate, bool)
                and isinstance(config_dto.headless_mode, bool)):
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
    determined_pause = 0.5
    divider = 2
    time.sleep(determined_pause + random.random() / divider)
    headers = config.get_headers()
    timeout = config.get_timeout()
    return requests.get(url,
                        headers=headers,
                        timeout=timeout,
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
        self._seed_urls = config.get_seed_urls()
        self._config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if isinstance(url, str):
            return url
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self._seed_urls:
            res = make_request(seed_url, self._config)
            html = BeautifulSoup(res.content, 'lxml')
            for paragraph in html.find_all('a', {'class': "news-list-card"}):
                if len(self.urls) >= self._config.get_num_articles():
                    return
                url = self._extract_url(paragraph)
                if not url or url in self.urls:
                    continue
                self.urls.append(url)

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
        article_content = article_soup.find("div", {'class': "article-body__content"})
        paragraphs = article_content.find_all("p")
        self.article.text = ' '.join(paragraph.text.strip() for paragraph in paragraphs)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1', class_="article-body__title")
        if title:
            self.article.title = title.text
        else:
            self.article.title = 'NOT FOUND'
        date = article_soup.find('div', class_="single-header__time")
        if date:
            try:
                self.article.date = self.unify_date_format(date.text)
            except ValueError:
                pass
        else:
            self.article.date = 'NOT FOUND'
        topics = [topic.text for topic in article_soup.find_all('a',
                                                                class_="single-header__rubric")]
        if topics:
            self.article.topics = topics[:-1]
            self.article.author = [-1]
        else:
            self.article.topics = ['NOT FOUND']
            self.article.author = 'NOT FOUND'

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        if not re.search(r'\d{4}', date_str):
            curr_year = datetime.date.today().year
            date_str = re.sub(r'(?<=[А-Яа-я])(?=,\s\d{2})',
                              f' {curr_year}', date_str)

            ru_eng_months = {
                "января": "jan",
                "февраля": "feb",
                "марта": "mar",
                "апреля": "apr",
                "мая": "may",
                "июня": "jun",
                "июля": "jul",
                "августа": "aug",
                "сентября": "sep",
                "октября": "oct",
                "ноября": "nov",
                "декабря": "dec"
            }

            ru_month = re.search(r"[а-я]{3,8}", date_str).group()
            date_str = date_str.replace(ru_month, ru_eng_months[ru_month])
            return datetime.datetime.strptime(date_str, '%d %b  %Y, %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        page = make_request(self.full_url, self.config)
        article_bs = BeautifulSoup(page.content, "lxml")
        self._fill_article_with_text(article_bs)
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
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for id_, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url,
                            article_id=id_,
                            config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
