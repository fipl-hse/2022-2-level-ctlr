"""
Crawler implementation
"""
import re
import json
import shutil
import datetime
from time import sleep
from pathlib import Path
from random import randint
from typing import Pattern, Union
import requests
from bs4 import BeautifulSoup
from core_utils.config_dto import ConfigDTO
from core_utils.article.article import Article
from core_utils.article.io import to_raw, to_meta
from core_utils.constants import (CRAWLER_CONFIG_PATH,
                                  ASSETS_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT,
                                  TIMEOUT_LOWER_LIMIT,
                                  TIMEOUT_UPPER_LIMIT)


class IncorrectSeedURLError(Exception):
    """
    Exception raised when seed_urls value in configuration
    file is not a list of strings or a string is not a valid URL
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Exception raised when total_articles_to_find_and_parse value
    in configuration file is out of range
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Exception raised when total_articles_to_find_and_parse
    value in configuration file is not an integer greater than 0
    """


class IncorrectHeadersError(Exception):
    """
    Exception raised when headers value in configuration file is not a dictionary
    """


class IncorrectEncodingError(Exception):
    """
    Exception raised when encoding value in configuration file is not a string
    """


class IncorrectTimeoutError(Exception):
    """
    Exception raised when timeout value in configuration file
    is not an integer between 1 and 30
    """


class IncorrectVerifyError(Exception):
    """
    Exception raised when should_verify_certificate
    value in configuration file is not a boolean
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
        config_file = self._extract_config_content()
        self._seed_urls = config_file.seed_urls
        self._num_articles = config_file.total_articles
        self._headers = config_file.headers
        self._encoding = config_file.encoding
        self._timeout = config_file.timeout
        self._should_verify_certificate = config_file.should_verify_certificate
        self._headless_mode = config_file.headless_mode

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
        config = self._extract_config_content()

        seed_urls = config.seed_urls
        if not isinstance(seed_urls, list) \
                or not all(isinstance(url, str) for url in seed_urls):
            raise IncorrectSeedURLError("Invalid value for seed_urls in configuration file")

        for seed_url in seed_urls:
            if not re.match(r'^https?://w?w?w?.', seed_url) and not seed_url.startswith(
                    'https://chelny-izvest.ru/news/'):
                raise IncorrectSeedURLError("Invalid seed URL in configuration file")

        total_articles_to_find_and_parse = config.total_articles
        if not isinstance(total_articles_to_find_and_parse, int) \
                or total_articles_to_find_and_parse < 1:
            raise IncorrectNumberOfArticlesError(
                "Invalid value for total_articles_to_find_and_parse in configuration file")

        if total_articles_to_find_and_parse > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError(
                "Invalid value for total_articles_to_find_and_parse in configuration file")

        headers = config.headers
        if not isinstance(headers, dict):
            raise IncorrectHeadersError("Invalid value for headers in configuration file")

        encoding = config.encoding
        if not isinstance(encoding, str):
            raise IncorrectEncodingError("Invalid value for encoding in configuration file")

        timeout = config.timeout
        if not isinstance(timeout, int) \
                or timeout < TIMEOUT_LOWER_LIMIT or timeout > TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError("Invalid value for timeout in configuration file")

        should_verify_certificate = config.should_verify_certificate
        if not isinstance(should_verify_certificate, bool):
            raise IncorrectVerifyError(
                "Invalid value for should_verify_certificate in configuration file")

        headless_mode = config.headless_mode
        if not isinstance(headless_mode, bool):
            raise IncorrectVerifyError("Invalid value for headless_mode in configuration file")

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
    wait_time = randint(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)
    sleep(wait_time)
    response = requests.get(url,
                            headers=config.get_headers(),
                            timeout=config.get_timeout(),
                            verify=config.get_verify_certificate())
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
        all_links_bs = article_bs.find_all('a')
        for link_bs in all_links_bs:
            href = link_bs.get('href')
            if href is None:
                continue
            if href.startswith('https://chelny-izvest.ru/news/') and href.count('/') == 5:
                return href

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self.get_search_urls():
            response = make_request(seed_url, self.config)
            if response.status_code != 200 or response.status_code == 404:
                continue
            article_bs = BeautifulSoup(response.text, 'lxml')
            article_url = self._extract_url(article_bs)
            while len(self.urls) < self.config.get_num_articles():
                self.urls.append(article_url)

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
        text_elements = article_soup.find("div", class_="page-main__text").find_all("p")
        self.article.text = "\n".join([p.get_text().strip() for p in text_elements])

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        author_elem = article_soup.find_all('a', class_='page-main__publish-author global-link')[0]
        authors = [author_elem.get_text(strip=True)] if author_elem else ["NOT FOUND"]

        date_elem = article_soup.find_all('a', class_='page-main__publish-date')[0]
        date_str = date_elem.get_text(strip=True) if date_elem else "NOT FOUND"
        date = self.unify_date_format(date_str)

        category_elem = article_soup.find_all('a', class_='panel-group__title global-link')[1]
        category = category_elem.get_text(strip=True) if category_elem else "NOT FOUND"

        title_elem = article_soup.find_all('h1', class_='page-main__head')[0]
        title = title_elem.get_text(strip=True) if title_elem else "NOT FOUND"

        self.article.author = authors
        self.article.date = date
        self.article.category = category
        self.article.title = title

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        months_dict = {
            "января": "January",
            "февраля": "February",
            "марта": "March",
            "апреля": "April",
            "мая": "May",
            "июня": "June",
            "июля": "July",
            "августа": "August",
            "сентября": "September",
            "октября": "October",
            "ноября": "November",
            "декабря": "December"
        }
        date_str = date_str.replace(date_str.split()[1], months_dict[date_str.split()[1]])
        date_obj = str(datetime.datetime.strptime(date_str, '%d %B %Y - %H:%M'))
        return datetime.datetime.strptime(date_obj, '%Y-%m-%d %H:%M:%S')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        article_soup = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article_soup)
        self._fill_article_with_meta_information(article_soup)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    assets_path = Path(base_path).joinpath(ASSETS_PATH)
    if assets_path.exists() and assets_path.is_dir():
        shutil.rmtree(assets_path)
    assets_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    config = Config(CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config)
    crawler.find_articles()
    for ind, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(url, ind, config)
        article = parser.parse()
        to_raw(article)
        to_meta(article)


if __name__ == "__main__":
    main()
