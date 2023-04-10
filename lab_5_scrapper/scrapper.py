"""
Crawler implementation
"""
import datetime
import json
import random
import re
import time
import shutil
from pathlib import Path
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_raw, to_meta
from core_utils.config_dto import ConfigDTO
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH, TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT


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
            seed_urls = config_content['seed_urls']
            headers = config_content['headers']
            num_of_articles = config_content['total_articles_to_find_and_parse']
            encoding = config_content['encoding']
            timeout = config_content['timeout']
            should_verify_certificate = config_content['should_verify_certificate']
            headless_mode = config_content['headless_mode']
        return ConfigDTO(seed_urls, num_of_articles,  headers, encoding,
                         timeout, should_verify_certificate, headless_mode)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config = self._extract_config_content()

        if not isinstance(config.seed_urls, list):
            raise IncorrectSeedURLError

        for url in config.seed_urls:
            if not re.fullmatch(r'https://w?w?w?.+', url):
                raise IncorrectSeedURLError

        if not isinstance(config.total_articles, int) or config.total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if config.total_articles > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(config.timeout, int) or config.timeout < 0 or config.timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(config.should_verify_certificate, bool) or not isinstance(config.headless_mode, bool):
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
    time.sleep((random.randint(3, 7)))
    response = requests.get(url, timeout=config.get_timeout(), headers=config.get_headers())
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
        if re.fullmatch(r'/novosti/.+', article_bs['href']):
            return 'https://www.vgoroden.ru' + article_bs['href']



    def find_articles(self) -> None:
        """
        Finds articles
        """
        #считывает только 36 ссылок, нужно исправить
        for url in self.config.get_seed_urls():
            response = make_request(url, self.config)
            res_bs = BeautifulSoup(response.text, 'lxml')
            for link in res_bs.find_all('a'):
                article_url = self._extract_url(link)
                if article_url is None:
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
        self.article.title = article_soup.find('h1', {'class': 'title'}).text
        self.article.author = article_soup.find('span', {'class': 'toolbar-opposite__author-text'}).text
        date_bs = article_soup.find('time', {'class': 'toolbar__text'})['datetime']
        date_and_time = ' '.join(re.findall(r'\d{4}-\d{2}-\d{2}', date_bs) + re.findall(r'\d{2}:\d{2}:\d{2}', date_bs))
        date = self.unify_date_format(date_and_time)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        dt_object = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return dt_object

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
