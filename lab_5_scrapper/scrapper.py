"""
Crawler implementation
"""
import datetime
import json
import os
import random
import re
import shutil
import time
from pathlib import Path
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

import core_utils.constants as const
from core_utils.article.article import Article
from core_utils.article.io import to_meta, to_raw
from core_utils.config_dto import ConfigDTO


class IncorrectSeedURLError(Exception):
    """
    Raised when seed URL does not match standard pattern
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Raised when total number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Raised when the total number of articles to parse is not an integer
    """


class IncorrectHeadersError(Exception):
    """
    Raised when headers are not in a form of dictionary
    """


class IncorrectEncodingError(Exception):
    """
    Raised when there is an invalid value for encoding
    """


class IncorrectTimeoutError(Exception):
    """
    Raised when timeout value is not a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    Raised when the verify certificate value is invalid
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
        with open(self.path_to_config, 'r', encoding='utf-8') as infile:
            reader = json.load(infile)
        return ConfigDTO(**reader)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()

        if not config_dto.seed_urls or not isinstance(config_dto.seed_urls, list):
            raise IncorrectSeedURLError

        for url in config_dto.seed_urls:
            if not isinstance(url, str) or not re.match(r'https?://.*/', url):
                raise IncorrectSeedURLError

        if (not isinstance(config_dto.total_articles, int)
                or isinstance(config_dto.total_articles, bool)
                or config_dto.total_articles < 1):
            raise IncorrectNumberOfArticlesError

        if config_dto.total_articles > const.NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError

        if (not isinstance(config_dto.timeout, int)
                or config_dto.timeout < const.TIMEOUT_LOWER_LIMIT
                or config_dto.timeout > const.TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError

        if (not isinstance(config_dto.should_verify_certificate, bool)
                or not isinstance(config_dto.headless_mode, bool)):
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
    response = requests.get(url, timeout=config.get_timeout(), headers=config.get_headers(),
                            verify=config.get_verify_certificate())
    response.encoding = config.get_encoding()
    time.sleep(random.uniform(2, 6))
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
        self._seed_urls = config.get_seed_urls()
        self._config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        href = article_bs.get('href')
        if href is not None:
            return str(href).lstrip('/news')
        return ""

    def find_articles(self) -> None:
        """
        Finds articles
        """
        start_url = self._config.get_seed_urls()[0]
        url = start_url
        count_of_page = 1
        while len(self.urls) < self._config.get_num_articles():
            page = make_request(url, config=self._config)
            if page.status_code == 200:
                soup = BeautifulSoup(page.text, features="html.parser")
                for elem in soup.find_all('a', class_='news-list__title'):
                    href = self._extract_url(elem)
                    if not href:
                        continue
                    current_url = start_url + href
                    if current_url not in self.urls:
                        self.urls.append(current_url)
                    if len(self.urls) >= self._config.get_num_articles():
                        return
                count_of_page += 1
                url = f"{start_url}/?PAGEN_1={count_of_page}"
            else:
                return

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
        self._config = config
        self.article = Article(full_url, article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        content_bs = article_soup.find('div', {'class': 'news-detail__text'})
        if content_bs:
            self.article.text += ' '.join(content_bs.text.split())
        text = ''
        if content_bs.find_all('p'):
            for p_tag in content_bs.find_all('p'):
                text += p_tag.text.strip()
            self.article.text += text

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1')
        self.article.title = title.text.strip()

        span_author = article_soup.find('span', itemprop='name')
        if span_author:
            self.article.author = [span_author.text]
        else:
            self.article.author = ['NOT FOUND']

        div_date = article_soup.find('meta', itemprop="datePublished")

        self.article.date = self.unify_date_format(div_date.get('content').strip())

        topics = article_soup.find('div', class_='tags__items')
        if topics:
            lst = []
            for elem in topics.find_all('a'):
                lst.append(elem.text)
            self.article.topics = lst

    @staticmethod
    def unify_date_format(date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%Y-%m-%d')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        page = make_request(self.full_url, self._config)
        if page.status_code == 200:
            soup = BeautifulSoup(page.text, "html.parser")
            self._fill_article_with_text(soup)
            self._fill_article_with_meta_information(soup)
            return self.article
        return False


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if base_path.exists():
        shutil.rmtree(base_path)
    os.makedirs(base_path)


class CrawlerRecursive(Crawler):
    """
     Recursive Crawler implementation
    """
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.count_of_page = 1
        self._config = config
        self.url = config.get_seed_urls()[0]
        self.load_info_from_file()

    def load_info_from_file(self) -> None:
        """
        Download information from a file
        """
        current_path = Path(__file__)
        crawler_data_path = current_path.parent / 'crawler_recursive_data.json'
        if crawler_data_path.exists():
            with open('crawler_recursive_data.json', 'r', encoding='utf-8') as infile:
                data = json.load(infile)
                self.count_of_page = data['count_of_page']
                self.urls = data['urls']

    def save_data_in_file(self) -> None:
        """
        Saving information into the file
        """
        data = {
            'count_of_page': self.count_of_page,
            'urls': self.urls
        }
        with open('crawler_recursive_data.json', 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile, ensure_ascii=True, indent=2)

    def find_articles(self) -> None:
        """
        Find articles
        """
        url = f"{self.url}?PAGEN_1={self.count_of_page}"
        page = make_request(url, self._config)
        soup = BeautifulSoup(page.text, "html.parser")
        for elem in soup.find_all('a', class_='news-list__title'):
            href = self._extract_url(elem)
            if not href:
                continue
            current_url = self.url + href
            if current_url in self.urls:
                continue
            self.urls.append(current_url)
            self.save_data_in_file()
            if len(self.urls) >= self._config.get_num_articles():
                return

        self.count_of_page += 1
        self.find_articles()


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    config = Config(const.CRAWLER_CONFIG_PATH)
    prepare_environment(const.ASSETS_PATH)
    crawler = Crawler(config)
    crawler.find_articles()
    for id_, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(full_url=url, article_id=id_, config=config)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


def main_recursive() -> None:
    """
    Entrypoint for Recursive Crawler
    """
    config = Config(const.CRAWLER_CONFIG_PATH)
    prepare_environment(const.ASSETS_PATH)
    crawler_recursive = CrawlerRecursive(config)
    crawler_recursive.find_articles()
    for id_, url in enumerate(crawler_recursive.urls, 1):
        parser = HTMLParser(full_url=url, article_id=id_, config=config)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
