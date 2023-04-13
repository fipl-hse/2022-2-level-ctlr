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
        return ConfigDTO(**config_content)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config = self._extract_config_content()

        if not isinstance(config.seed_urls, list):
            raise IncorrectSeedURLError

        for url in config.seed_urls:
            if not re.fullmatch(r'https://.+', url):
                raise IncorrectSeedURLError

        if not isinstance(config.total_articles, int)\
                or config.total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if config.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(config.timeout, int) or config.timeout < TIMEOUT_LOWER_LIMIT\
            or config.timeout > TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        if not isinstance(config.should_verify_certificate, bool) \
                or not isinstance(config.headless_mode, bool):
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
    time.sleep(random.randint(1, 3))
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
        self.seed_urls = self.config.get_seed_urls()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        href = article_bs.get('href')
        if href and isinstance(href, str) \
                and re.fullmatch(r'/novosti/.+id\d+', href):
            return href
        return ' '


    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.seed_urls:
            response = make_request(url, self.config)
            res_bs = BeautifulSoup(response.text, 'lxml')
            for link in res_bs.find_all('a'):
                if len(self.urls) >= self.config.get_num_articles():
                    return
                article_url = self._extract_url(link)
                if article_url is None or article_url == ' ' or ('https://www.vgoroden.ru' + article_url) in self.urls:
                    continue
                self.urls.append('https://www.vgoroden.ru' + article_url)



    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self.seed_urls


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
        article_body = article_soup.find('div', {'class' :'article__body'}).stripped_strings
        art_text = ' '.join(i for i in article_body)
        self.article.text = art_text

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
        if not author:
            self.article.author.append('NOT FOUND')
        date_bs = article_soup.find('time', {'class': 'toolbar__text'}).get('datetime')
        if isinstance(date_bs, str):
            date_and_time = re.search(r'\d{4}-\d{2}-\d{2}', date_bs).group() + \
                        ' ' + re.search(r'\d{2}:\d{2}:\d{2}', date_bs).group()
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
        self.counter = 0
        self.visited_urls = []
        self.path = Path(__file__).parent / 'r_crawler_data.json'

    def load_data(self):
        """
        Loads collected data from a file
        """
        if self.path.exists():
            with open ("r_crawler_data.json", encoding=self.config.get_encoding()) as f:
                data = json.load(f)



    def save_data(self):
        """
        Saves collected data to a file
        """
        data = {'start_url': self.start_url,
                'urls': self.urls}
        with open(self.path, 'w', encoding=self.config.get_encoding()) as f:
            json.dump(data, f, indent=4)


    def find_articles(self) -> None:
        """
        Finds URLs recursively starting from seed URL
        """
        if self.start_url not in self.visited_urls:
            self.visited_urls.append(self.start_url)
        else:
            self.visited_urls.append(self.urls[self.counter])
        response = make_request(self.visited_urls[self.counter], self.config)
        response_bs = BeautifulSoup(response.text, 'lxml')
        for link in response_bs.find_all('a'):
            article_url = self._extract_url(link)
            if len(self.urls) >= self.config.get_num_articles():
                return
            art_url = 'https://www.vgoroden.ru' + article_url
            if not article_url or article_url is None or article_url == ' ' or art_url in self.urls:
                continue
            self.urls.append(art_url)
        self.counter += 1
        self.find_articles()

def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(configuration)
    crawler.find_articles()
    a = crawler.urls
    print(len(a))
    for i, full_url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=full_url, article_id=i, config=configuration)
        article = parser.parse()
        if isinstance(article,Article):
            to_raw(article)
            to_meta(article)


def main_recursive() -> None:
    """
    Recursive crawling
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    r_crawler = CrawlerRecursive(configuration)
    r_crawler.find_articles()
    a = r_crawler.urls
    print(len(set(r_crawler.urls)))
    for i, full_url in enumerate(r_crawler.urls, start=1):
        parser = HTMLParser(full_url=full_url, article_id=i, config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)



if __name__ == "__main__":
    main_recursive()
