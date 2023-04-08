"""
Crawler implementation
"""
from typing import Pattern, Union
from pathlib import Path

import requests
from bs4 import BeautifulSoup

import re
import json
import time
import random
import shutil

from core_utils.config_dto import ConfigDTO
from core_utils.article.article import Article
from core_utils.constants import CRAWLER_CONFIG_PATH, ASSETS_PATH, TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT
from core_utils.article.io import to_raw
import datetime

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
        self._validate_config_content()
        self.seed_urls = self._extract_config_content().seed_urls
        self.headers = self._extract_config_content().headers
        self.num_of_articles = self._extract_config_content().total_articles
        self.encoding = self._extract_config_content().encoding
        self.timeout = self._extract_config_content().timeout
        self.should_verify_certificate = self._extract_config_content().should_verify_certificate



    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config_content = json.load(f)
            seed_urls = config_content['seed_urls']
            headers = config_content['headers']
            num_of_articles = config_content['total_articles_to_find_and_parse']
            encoding = config_content['encoding']
            timeout = config_content['timeout']
            should_verify_certificate = config_content['should_verify_certificate']
            headless_mode = config_content['headless_mode']
        return ConfigDTO(seed_urls, headers, num_of_articles, encoding,
                         timeout, should_verify_certificate, headless_mode)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config_content = json.load(f)
            seed_urls = config_content['seed_urls']
            headers = config_content['headers']
            total_articles_to_find_and_parse = config_content['total_articles_to_find_and_parse']
            encoding = config_content['encoding']
            timeout = config_content['timeout']
            should_verify_certificate = config_content['should_verify_certificate']
            headless_mode = config_content['headless_mode']

        if not isinstance(seed_urls, list):
            raise IncorrectSeedURLError

        for url in seed_urls:
            if not re.fullmatch(r'https://w?w?w?.+', url):
                raise IncorrectSeedURLError

        if total_articles_to_find_and_parse < 1 or total_articles_to_find_and_parse > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(total_articles_to_find_and_parse, int):
            raise IncorrectNumberOfArticlesError

        if not isinstance(headers, dict):
            raise  IncorrectHeadersError

        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        if timeout < 0 or timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(should_verify_certificate, bool):
            raise IncorrectVerifyError



    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.num_of_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.timeout


    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    time.sleep((random.randint(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)))
    response = requests.get(url,headers=config.get_headers(),
                            timeout=config.get_timeout())
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
            if re.fullmatch(r'/novosti/[0-9a-z-]+', link_bs['href']):
                return 'https://www.vgoroden.ru' + link_bs['href']


    def find_articles(self) -> None:
        """
        Finds articles
        """
        #смотри гайд для dynamic scrapping
        for url in self.config.get_seed_urls():
            response =  make_request(url, self.config)
            res_bs = BeautifulSoup(response.text, 'lxml')



    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        pass


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
        self.article = Article

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        article_body = article_soup.find('div', {'class': 'article__body'})
        article_text = article_body.find_all(['p', 'div', {'class': 'quote-text'}])

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        pass

    def unify_date_format(self, date_str: str)-> datetime.datetime:
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        pass


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    #или попробовать через трай эксепты?
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)



def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)



    #не забудь выполнить здесь пятый шаг


if __name__ == "__main__":
    main()
