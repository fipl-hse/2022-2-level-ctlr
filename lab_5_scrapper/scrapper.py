"""
Crawler implementation
"""
import datetime
from typing import Pattern, Union
from pathlib import Path
from core_utils.article.article import Article
from core_utils.config_dto import ConfigDTO
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH, NUM_ARTICLES_UPPER_LIMIT, TIMEOUT_LOWER_LIMIT, \
    TIMEOUT_UPPER_LIMIT
from core_utils.article.io import to_raw
import json
import requests
from random import randint
import shutil
import time
from bs4 import BeautifulSoup
import re


class IncorrectSeedURLError(Exception):
    """
    Seed URL does not match standard pattern or does not correspond to the target website
    """
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of the needed range
    """
    pass


class IncorrectNumberOfArticlesError(Exception):
    """
    Total number of articles to parse is not integer
    """
    pass


class IncorrectHeadersError(Exception):
    """
    Headers are not in a form of dictionary
    """
    pass


class IncorrectEncodingError(Exception):
    """
    Encoding must be specified as a string
    """
    pass


class IncorrectTimeoutError(Exception):
    """
    Incorrect timeout value
    """
    pass


class IncorrectVerifyError(Exception):
    """
    Incorrect verify certificate value
    """
    pass


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
        self.dto = self._extract_config_content()
        self._seed_urls = self.dto.seed_urls
        self._total_articles = self.dto.total_articles
        self._headers = self.dto.headers
        self._encoding = self.dto.encoding
        self._timeout = self.dto.timeout
        self._should_verify_certificate = self.dto.should_verify_certificate
        self._headless_mode = self.dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            parameters = json.load(file)
        return ConfigDTO(seed_urls=parameters['seed_urls'], headers=parameters['headers'],
                         total_articles_to_find_and_parse=parameters['total_articles_to_find_and_parse'],
                         encoding=parameters['encoding'], timeout=parameters['timeout'],
                         should_verify_certificate=parameters['should_verify_certificate'],
                         headless_mode=parameters['headless_mode'])

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            parameters = json.load(file)

        if not isinstance(parameters['seed_urls'], list):
            raise IncorrectSeedURLError

        for url in parameters['seed_urls']:
            if not (re.match(r'https?://w?w?w?.', url) and url.startswith('https://livennov.ru/news/')
                    and isinstance(url, str)):
                raise IncorrectSeedURLError

        if not isinstance(parameters['total_articles_to_find_and_parse'], int) or \
                parameters['total_articles_to_find_and_parse'] > NUM_ARTICLES_UPPER_LIMIT or \
                parameters['total_articles_to_find_and_parse'] <= 0:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(parameters['total_articles_to_find_and_parse'], int) or \
                isinstance(parameters['total_articles_to_find_and_parse'], bool):
            raise IncorrectNumberOfArticlesError

        if not isinstance(parameters['headers'], dict):
            raise IncorrectHeadersError

        if not isinstance(parameters['encoding'], str):
            raise IncorrectEncodingError

        if not isinstance(parameters['timeout'], int) or parameters['timeout'] < TIMEOUT_LOWER_LIMIT or \
                parameters['timeout'] > TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        if not (isinstance(parameters['should_verify_certificate'], bool)
                and isinstance(parameters['headless_mode'], bool)):
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
        return self._total_articles

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
    time.sleep(randint(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT))
    return requests.get(url, headers=config.get_headers(), timeout=config.get_timeout())


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
        self.seed_urls = config.get_seed_urls()
        self.number_of_articles = config.get_num_articles()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        all_links_bs = article_bs.find_all('a')
        for link in all_links_bs:
            href = link.get('href')
            total_digits = len(re.findall('[0-9]', href))
            if href is None:
                print(link)
                continue
            elif href.startswith('/news/') and total_digits >= 8:
                return "https://livennov.ru" + href

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for link in self.seed_urls:
            response = make_request(link, self.config)
            main_bs = BeautifulSoup(response.text, 'lxml')
            url = self._extract_url(main_bs)
            if url not in self.urls:
                self.urls.append(url)

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
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        self.main_text_bs = article_soup.find('div', {
            'itemprop': 'articleBody'
        }).text.replace('\n', '').replace('\n\n', ' ').replace('  ', '').strip()

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title_info = article_soup.find('div', {'class', 'b-news-detail-top'}).find('h1')
        if title_info:
            self.article.title = title_info.text

        author_info = article_soup.find('a', {'href': '/author/kiryan-latunskiy/'}).find('span', {'itemprop': 'name'})
        if author_info:
            self.article.author = author_info.text.strip()

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        main_bs = BeautifulSoup(response.content, "lxml")
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


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, full_url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=full_url, article_id=i, config=configuration)
        article = parser.parse()
        to_raw(article)

    # pass


if __name__ == "__main__":
    main()
