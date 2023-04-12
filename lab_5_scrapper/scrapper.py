"""
Crawler implementation
"""
import datetime
import json
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
    seed URL does not match standard pattern 'https?://w?w?w?.'
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
    encoding is not specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    timeout value is not a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    verify certificate value is not True or False
    """


class Config:
    """
    Unpacks and validates configurations
    """

    seed_urls: list[str]
    total_articles_to_find_and_parse: int
    headers: dict[str, str]
    encoding: str
    timeout: int
    verify_certificate: bool
    headless_mode: bool

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
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return ConfigDTO(**config_dict)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as config_file:
            config_content = json.load(config_file)

        seed_urls = config_content['seed_urls']
        headers = config_content['headers']
        total_articles_to_find_and_parse = config_content['total_articles_to_find_and_parse']
        encoding = config_content['encoding']
        timeout = config_content['timeout']
        verify_certificate = config_content['should_verify_certificate']
        headless_mode = config_content['headless_mode']

        if not isinstance(seed_urls, list):
            raise IncorrectSeedURLError

        for url in seed_urls:
            if not isinstance(url, str):
                raise IncorrectSeedURLError
            if not re.match(r'https?://.*/', url):
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
    headers = config.get_headers()
    timeout = config.get_timeout()
    verify = config.get_verify_certificate()
    response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
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
        url = article_bs['href']
        if isinstance(url, str):
            return url
        return url[0]

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self._seed_urls:
            response = make_request(seed_url, self._config)
            if response.status_code != 200:
                continue
            main_bs = BeautifulSoup(response.text, 'lxml')
            all_links_bs = main_bs.find_all('a')
            for link_bs in all_links_bs:
                href = self._extract_url(link_bs)
                if href is None:
                    print(link_bs)
                    continue
                if href.startswith('/news') or href.startswith('/gov') or href.startswith(
                        '/society') or href.startswith('/business'):
                    if href.count('/') == 3 and 'comment' not in href:
                        found_url = "https://chelny-biz.ru" + href
                        if found_url not in self.urls:
                            if len(self.urls) < self._config.get_num_articles():
                                self.urls.append(found_url)

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
        self.article_id = article_id
        self._config = config
        self.article = Article(self._full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        text = []
        text_str = ''
        text_bs = article_soup.find(class_="pin-text wid")
        article = article_soup.find_all("p")
        if article:
            for paragraph in article:
                cleaned_paragraph = paragraph.text.strip()
                if cleaned_paragraph:
                    text.append(cleaned_paragraph)
            text_str = "\n".join(text)
        if len(text_str) < 50:
            text_str = text_bs.get_text(strip=True)
        self.article.text = text_str

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title_bs = article_soup.find_all('h1')
        self.article.title = title_bs[0].text

        self.article.author = ["NOT FOUND"]
        self.article.topics = []

        date = article_soup.find_all(class_="pin-date wid bs-bb")[0].text
        self.article.date = self.unify_date_format(date)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%d.%m.%Y, %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self._full_url, self._config)
        if response.status_code == 200:
            a_bs = BeautifulSoup(response.text, 'lxml')
            self._fill_article_with_text(a_bs)
            self._fill_article_with_meta_information(a_bs)
            return self.article
        return False


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
    for i, url in enumerate(crawler.urls):
        parser = HTMLParser(full_url=url, article_id=i+1, config=config)
        text = parser.parse()
        if isinstance(text, Article):
            to_raw(text)
            to_meta(text)


if __name__ == "__main__":
    main()
