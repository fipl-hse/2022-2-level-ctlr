"""
Crawler implementation
"""
import datetime
import json
from pathlib import Path
from typing import Pattern, Union
from urllib.parse import urlparse

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
    Validates a seed url format
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Validates the number of articles within the necessary range
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Validates the type of number of articles
    """


class IncorrectHeadersError(Exception):
    """
    Validates the type of header
    """


class IncorrectEncodingError(Exception):
    """
    Validates the type of encoding
    """


class IncorrectTimeoutError(Exception):
    """
    Validates timeout
    """


class IncorrectVerifyError(Exception):
    """
    Validates the verify attribute
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
            info = json.load(file)

        config_dto = ConfigDTO(info['seed_urls'],
                               info['total_articles_to_find_and_parse'],
                               info['headers'],
                               info['encoding'],
                               info['timeout'],
                               info['should_verify_certificate'],
                               info['headless_mode'])

        return config_dto

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:

            info = json.load(file)
        seed_urls = info['seed_urls']
        headers = info['headers']
        total_articles_to_find_and_parse = info['total_articles_to_find_and_parse']
        encoding = info['encoding']
        timeout = info['timeout']
        verify_certificate = info['should_verify_certificate']
        headless_mode = info['headless_mode']

        if not isinstance(seed_urls, list):
            raise IncorrectSeedURLError

        for url in seed_urls:
            result = urlparse(url)
            if (not isinstance(url, str)
                    or not result.netloc or not result.scheme):
                raise IncorrectSeedURLError

        if (not isinstance(total_articles_to_find_and_parse, int)
                or isinstance(total_articles_to_find_and_parse, bool)
                or total_articles_to_find_and_parse < 1):
            raise IncorrectNumberOfArticlesError

        if total_articles_to_find_and_parse > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        if (not isinstance(timeout, int)
                or timeout < TIMEOUT_LOWER_LIMIT
                or timeout > TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError

        if not isinstance(verify_certificate, bool):
            raise IncorrectVerifyError

        if not isinstance(headless_mode, bool):
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
    return requests.get(url, headers=config.get_headers(), timeout=config.get_timeout(),
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
        self.urls = []
        self._config = config
        self._seed_urls = config.get_seed_urls()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs['href']
        if isinstance(url, str):
            return url
        return url[0]

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed in self._seed_urls:
            response = make_request(seed, self._config)
            soup = BeautifulSoup(response.text, 'lxml')
            for url in soup.find_all('a', class_="news-line_newsLink__e0zuO"):
                part_of_url = self._extract_url(url)
                if (len(self.urls) < self._config.get_num_articles()
                        and 'specials' not in part_of_url):
                    self.urls.append('https://progorod76.ru' + part_of_url)

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
        for text in article_soup.find_all('p')[:-2]:
            self.article.text += text.text + '\n'

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1', attrs={'itemprop': 'headline'})
        if title:
            self.article.title = title.text

        author = article_soup.find('a', class_='article-info_articleInfoAuthor__W0ZnW')
        if author:
            self.article.author = [author.text]
        if not author:
            self.article.author = ["NOT FOUND"]

        topics = article_soup.find_all("a", class_='article-tags_articleTagsLink__El86x')
        if topics:
            self.article.topics = [topic.text for topic in topics]

        date = article_soup.find('span', attrs={'class': 'article-info_articleInfoDate__S0E0P'})
        string_date = date.text
        list_date = string_date.lower().split()

        months_collection = {"января": "01", "февраля": "02", "марта": "03",
                             "апреля": "04", "мая": "05", "июня": "06",
                             "июля": "07", "августа": "08", "сентября": "09",
                             "октября": "10", "ноября": "11", "декабря": "12"}

        year = '2023'
        month = ''
        day = ''
        time = ''

        for element in list_date:
            if ':' in element:
                time += element
            if element in months_collection:
                month += months_collection[element]
            digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
            if element.isdigit() and element in digits:
                day += '0' + element
            if element.isdigit() and element not in digits:
                day += element

        self.article.date = self.unify_date_format(year + '-' + month + '-' + day + ' ' + time)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        page = make_request(self._full_url, self._config)
        soup = BeautifulSoup(page.text, "lxml")
        self._fill_article_with_text(soup)
        self._fill_article_with_meta_information(soup)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if base_path.exists():
        base_path.rmdir()
    base_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    config = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=config)
    crawler.find_articles()
    for idx, url in enumerate(crawler.urls):
        parser = HTMLParser(full_url=url, article_id=idx+1, config=config)
        text = parser.parse()
        if isinstance(text, Article):
            to_raw(text)
            to_meta(text)


if __name__ == "__main__":
    main()
