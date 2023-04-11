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
    Exception raised when seed_urls value is not a list
    or does not match a standard pattern
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Exception raised when total number of articles to find
    is more than 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Exception raised when total number of articles to find
    is not a positive integer
    """


class IncorrectHeadersError(Exception):
    """
    Exception raised when headers value is not a dictionary
    """


class IncorrectEncodingError(Exception):
    """
    Exception raised when encoding value is not a string
    """


class IncorrectTimeoutError(Exception):
    """
    Exception raised when timeout value is not a positive integer
    or is more than 60
    """


class IncorrectVerifyError(Exception):
    """
    Exception raised when should_verify_certificate value
    or headless_mode value is not a boolean
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
        self.config = self._extract_config_content()
        self._seed_urls = self.config.seed_urls
        self._headers = self.config.headers
        self._num_articles = self.config.total_articles
        self._encoding = self.config.encoding
        self._timeout = self.config.timeout
        self._should_verify_certificate = self.config.should_verify_certificate
        self._headless_mode = self.config.headless_mode



    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config_content = json.load(f)
        return ConfigDTO(config_content['seed_urls'],
                         config_content['total_articles_to_find_and_parse'],
                         config_content['headers'],
                         config_content['encoding'],
                         config_content['timeout'],
                         config_content['should_verify_certificate'],
                         config_content['headless_mode'])

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config = self._extract_config_content()
        seed_urls = config.seed_urls
        total_articles = config.total_articles
        headers = config.headers
        encoding = config.encoding
        timeout = config.timeout
        verify_certificate = config.should_verify_certificate
        headless_mode = config.headless_mode

        if not isinstance(seed_urls, list):
            raise IncorrectSeedURLError

        for url in seed_urls:
            if not re.fullmatch(r'https://.+', url):
                raise IncorrectSeedURLError

        if not isinstance(total_articles, int) or total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        if not isinstance(timeout, int) or timeout < 0 or timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(verify_certificate, bool) or not isinstance(headless_mode, bool):
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
    time.sleep((random.randint(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)))
    response = requests.get(url, timeout=config.get_timeout(), headers=config.get_headers())
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
        if article_bs.get('href') and re.fullmatch(r'/novosti/.+', article_bs['href'][0]):
            return article_bs['href'][0]
        return ' '



    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.config.get_seed_urls():
            response = make_request(url, self.config)
            res_bs = BeautifulSoup(response.text, 'lxml')
            for link in res_bs.find_all('a'):
                article_url = 'https://www.vgoroden.ru' + self._extract_url(link)
                if article_url is None or article_url == ' ':
                    continue
                self.urls.append(article_url)
                if len(self.urls) == self.config.get_num_articles():
                    break


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
        self.article = Article(full_url, article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        article_body = article_soup.find('div', {'class': 'article__body'})
        article_text = article_body.find_all(['p', 'div', {'class': 'quote-text'}])
        art_text = [i.text for i in article_text]
        self.article.text = '\n'.join(art_text)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1', {'class': 'title'}).text
        if title:
            self.article.title = title
        author = article_soup.find('span', {'class': 'toolbar-opposite__author-text'}).text
        if author:
            self.article.author.append(author)
        date_bs = article_soup.find('time', {'class': 'toolbar__text'})['datetime']
        date_and_time = ' '.join(re.findall(r'\d{4}-\d{2}-\d{2}', date_bs[0])
                                 + re.findall(r'\d{2}:\d{2}:\d{2}', date_bs[0]))
        self.article.date = self.unify_date_format(date_and_time)
        topic = article_soup.find('a', {'class': 'toolbar__item toolbar__main-link'}).text
        if topic:
            self.article.topics.append(topic)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        soup = make_request(self.full_url, self.config)
        article_bs = BeautifulSoup(soup.text, 'lxml')
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

class CrawlerRecursive(Crawler):
    """
    Recursive crawler implementation
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes the instance of CrawlerRecursive class
        """
        super().__init__(config)
        self.start_url = config.get_seed_urls()[0]



def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(configuration)
    crawler.find_articles()
    print(crawler.get_search_urls())
    print(len(crawler.get_search_urls()))
    for i, full_url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=full_url, article_id=i, config=configuration)
        article = parser.parse()
        to_raw(article)
        to_meta(article)


if __name__ == "__main__":
    main()
