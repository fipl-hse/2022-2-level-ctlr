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
from core_utils.config_dto import ConfigDTO


class IncorrectSeedURLError(Exception):
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    pass


class IncorrectNumberOfArticlesError(Exception):
    pass


class IncorrectHeadersError(Exception):
    pass


class IncorrectEncodingError(Exception):
    pass


class IncorrectTimeoutError(Exception):
    pass


class IncorrectVerifyError(Exception):
    pass


class Config:
    """
    Unpacks and validates configurations
    """

    def __init__(self, path_to_config: Path) -> None:
        """
        Initializes an instance of the Config class
        """
        self.path_to_config = path_to_config
        self._config_dto = self._extract_config_content()
        self._validate_config_content()

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

        if not isinstance(config_dto.seed_urls, list):
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
        return self._config_dto.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self._config_dto.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self._config_dto.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self._config_dto.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self._config_dto.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self._config_dto.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self._config_dto.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    time.sleep(random.randint(const.TIMEOUT_LOWER_LIMIT, const.TIMEOUT_UPPER_LIMIT))
    response = requests.get(url,
                            timeout=config.get_timeout(),
                            headers=config.get_headers(),
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
        self._urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        href = article_bs.get('href')
        return href

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.config.get_seed_urls():
            page = make_request(url, config=self.config)
            page.encoding = self.config.get_encoding()
            soup = BeautifulSoup(page.text, features="html.parser")
            for elem in soup.find_all('a', class_='news-list__title'):
                current_url = url + self._extract_url(elem)
                if current_url is not None:
                    self._urls.append(current_url)
                if len(self._urls) >= self.config.get_num_articles():
                    return

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._urls


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
            text = ''
            for p in content_bs.find_all('p'):
                text += p.text.strip()
            self.article.text = text

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1')
        if title:
            self.article.title = title.text.strip()

        span_author = article_soup.find('span', itemprop='name')
        if span_author:
            self.article.author = span_author.text

        div_date = article_soup.find_all('div', class_='news-detail__info-item')[1]
        if div_date:
            try:
                self.article.date = self.unify_date_format(div_date.text.strip())
            except ValueError:
                pass

    @staticmethod
    def unify_date_format(date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%d.%m.%Y')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        page = make_request(self.full_url, self._config)
        page.encoding = self._config.get_encoding()
        soup = BeautifulSoup(page.text, features="html.parser")
        self._fill_article_with_text(soup)
        self._fill_article_with_meta_information(soup)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if base_path.exists():
        shutil.rmtree(base_path)
    os.makedirs(base_path)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    config = Config(const.CRAWLER_CONFIG_PATH)
    prepare_environment(const.ASSETS_PATH)
    crawler = Crawler(config)
    crawler.find_articles()
    for id_, url in enumerate(crawler.get_search_urls()):
        parser = HTMLParser(full_url=url, article_id=id_, config=config)
        article = parser.parse()


if __name__ == "__main__":
    main()
