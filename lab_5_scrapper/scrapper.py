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
    Seed URL does not match standard pattern or does not correspond to the target website
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of the needed range
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
    Incorrect timeout value
    """


class IncorrectVerifyError(Exception):
    """
    Incorrect verify certificate value
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
        dto = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = dto.seed_urls
        self._num_articles = dto.total_articles
        self._headers = dto.headers
        self._encoding = dto.encoding
        self._timeout = dto.timeout
        self._should_verify_certificate = dto.should_verify_certificate
        self._headless_mode = dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            parameters = json.load(file)
        return ConfigDTO(**parameters)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        dto = self._extract_config_content()

        if not dto.seed_urls or not isinstance(dto.seed_urls, list):
            raise IncorrectSeedURLError("Invalid value for seed_urls")

        for url in dto.seed_urls:
            if not isinstance(url, str) or not re.match(r'https?://', url):
                raise IncorrectSeedURLError("Invalid seed url")

        if (not isinstance(dto.total_articles, int)
                or isinstance(dto.total_articles, bool)
                or dto.total_articles < 1):
            raise IncorrectNumberOfArticlesError(
                "Invalid value for total_articles_to_find_and_parse")

        if dto.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError(
                "Invalid value for total_articles_to_find_and_parse")

        if not isinstance(dto.headers, dict):
            raise IncorrectHeadersError("Invalid value for headers")

        if not isinstance(dto.encoding, str):
            raise IncorrectEncodingError("Invalid value for encoding")

        if (not isinstance(dto.timeout, int)
                or dto.timeout < TIMEOUT_LOWER_LIMIT
                or dto.timeout > TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError("Invalid value for timeout")

        if not isinstance(dto.should_verify_certificate, bool) or \
                not isinstance(dto.headless_mode, bool):
            raise IncorrectVerifyError(
                "Invalid value for should_verify_certificate or headless_mode")

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
    response = requests.get(url, headers=config.get_headers(), timeout=config.get_timeout(),
                            verify=config.get_verify_certificate())
    response.encoding = config.get_encoding()
    time.sleep(random.randrange(2, 7))
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
        self.config = config
        self.number_of_articles = config.get_num_articles()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if url and isinstance(url, str) \
                and url.startswith('https://moskvichmag.ru/gorod/'):
            return url
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.get_search_urls():
            response = make_request(url, self.config)
            main_bs = BeautifulSoup(response.text, "lxml")
            for link in main_bs.find_all('a'):
                if (url := self._extract_url(link)) and url not in self.urls:
                    self.urls.append(url)
                if len(self.urls) >= self.config.get_num_articles():
                    return

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
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        main_text = article_soup.find('div', {
            'itemprop': 'articleBody'})
        self.article.text = main_text.get_text(strip=True)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title_info = article_soup.find('h1', itemprop="headline")
        self.article.title = title_info.text

        author_info = article_soup.find('span', itemprop="name")
        if not author_info.text:
            self.article.author.append('NOT FOUND')
        self.article.author.append(author_info.text)

        date_info = article_soup.find('time', {
            'class': "entry-date published ArticlesItem-datetime"})
        if date_info:
            self.article.date = self.unify_date_format(date_info.text)

        for topic in article_soup.find_all('a', {"class": "Article-category"}):
            if topic.text and topic.text not in self.article.topics:
                self.article.topics.append(topic.text)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%d.%m.%Y')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        main_bs = BeautifulSoup(response.text, "lxml")
        self._fill_article_with_text(main_bs)
        self._fill_article_with_meta_information(main_bs)
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
    Recursive Crawler implementation
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the Recursive Crawler class
        """
        super().__init__(config)
        self.start_url = config.get_seed_urls()[0]
        self.rec_crawler_path = Path(__file__).parent / 'rec_crawler_meta.json'
        self.load_data()

    def load_data(self) -> None:
        """
        Downloads information
        """
        if self.rec_crawler_path.exists():
            with open(self.rec_crawler_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            self.start_url = data['start_url']
            self.urls = data['urls']

    def save_data(self) -> None:
        """
        Saves received information into the file
        """
        data = {'start_url': self.start_url,
                'urls': self.urls}

        with open(self.rec_crawler_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

    def find_articles(self) -> None:
        """
        Finds articles
        """
        response = make_request(self.start_url, self.config)
        article_bs = BeautifulSoup(response.text, 'lxml')
        for link in article_bs.find_all('a'):
            if len(self.urls) >= self.config.get_num_articles():
                return
            if self._extract_url(link) and \
                    self._extract_url(link) not in self.urls:
                self.urls.append(self._extract_url(link))
                self.save_data()

        new_start = article_bs.find('a',
                                    class_="Loader-btn").get('href')
        self.start_url = str(new_start)
        self.save_data()
        self.find_articles()


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=i, config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


def main2() -> None:
    """
    Entrypoint for recursive scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler_recursive = CrawlerRecursive(config=configuration)
    crawler_recursive.find_articles()
    for i, url in enumerate(crawler_recursive.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=i, config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main2()
