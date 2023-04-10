"""
Crawler implementation
"""
import datetime
import os
import re
import shutil
import time
from pathlib import Path
import random
from typing import Pattern, Union
import json

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.config_dto import ConfigDTO

import core_utils.constants as const


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
        pattern = r"^https?://[-a-zA-Z0-9+&@#/%?=~_|!:,.;]*[-a-zA-Z0-9+&@#/%=~_|]"
        if not self._config_dto.seed_urls or not isinstance(self._config_dto.seed_urls, list) \
                or not all(isinstance(url, str) for url in self._config_dto.seed_urls) \
                or not all(re.fullmatch(pattern, url) for url in self._config_dto.seed_urls):
            raise IncorrectSeedURLError

        if not isinstance(self._config_dto.total_articles, int) \
                or self._config_dto.total_articles > const.NUM_ARTICLES_UPPER_LIMIT:
            raise IncorrectNumberOfArticlesError

        if not self._config_dto.seed_urls and not isinstance(self._config_dto.headers, dict) \
                and not all(isinstance(key, str) and isinstance(value, str)
                            for key, value in self._config_dto.headers.items()):
            raise IncorrectHeadersError

        if not isinstance(self._config_dto.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(self._config_dto.timeout, int) or self._config_dto.timeout < const.TIMEOUT_LOWER_LIMIT \
                or self._config_dto.timeout > const.TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        if not isinstance(self._config_dto.should_verify_certificate, bool):
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

    @staticmethod
    def _extract_url(article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        link = article_bs.find('a')
        href = link.get('href')
        return href

    def find_articles(self) -> None:
        """
        Finds articles
        """
        url = self.config.get_seed_urls()[0]
        count_of_page = 1
        while len(self._urls) < self.config.get_num_articles():
            print('while')
            page = make_request(url, config=self.config)
            page = page.content.decode(self.config.get_encoding())
            soup = BeautifulSoup(page, features="html.parser")
            h3_with_articles = soup.find_all('h3')
            for elem in h3_with_articles:
                url = self._extract_url(elem)
                if url is not None:
                    self._urls.append(url)
                if len(self._urls) >= self.config.get_num_articles():
                    return
            count_of_page += 1
            url = f"{url}/page/{count_of_page}"

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
        self.config = config
        self.article = Article(full_url, article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        div = article_soup.find('div', class_='entry-content')
        text = ''
        for p in div.find_all('p'):
            if 'Фото:' in p.text or re.search(r'\([0-9]+\+\)', p.text):
                break
            text += p.text
        self.article.text = text

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        div_date = article_soup.find('div', style='padding-left: 30px; padding-bottom: 10px;')
        if div_date:
            try:
                self.article.date = self.unify_date_format(div_date.text)
                print(self.article.date)
            except ValueError:
                pass
        span_author = article_soup.find('span', class_='name')
        if span_author:
            a_author = span_author.find('a')
            if a_author:
                print(a_author.text)
                self.article.author = a_author.text

        title = article_soup.find('h1')
        if title:
            print(title.text)
            self.article.title = title.text

    @staticmethod
    def unify_date_format(date_str: str) -> datetime.datetime:
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
        date_list = date_str.split()
        month = months_dict[date_list[1]]
        date_list[1] = month
        date_str = ' '.join(date_list)
        return datetime.datetime.strptime(date_str, '%d %B %Y в %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        page = make_request(self.full_url, self.config)
        page.encoding = self.config.get_encoding()
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


if __name__ == "__main__":
    main()
