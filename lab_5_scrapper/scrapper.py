"""
Crawler implementation
"""
from typing import Pattern, Union
import datetime
from core_utils.article.article import Article
from pathlib import Path
import json
import requests
import re
import shutil
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (ASSETS_PATH, CRAWLER_CONFIG_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT)
from urllib.parse import urlparse
from core_utils.article.io import to_meta, to_raw


class IncorrectSeedURLError(Exception):
    """
    Raised when the seed URL does not match the
    standard pattern or does not correspond to the target website
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Raised when the total number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Raised when the total number of articles to parse is not an integer
    """


class IncorrectHeadersError(Exception):
    """
    Raised when headers are not in the form of a dictionary
    """


class IncorrectEncodingError(Exception):
    """
    Raised when the encoding is not specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    Raised when the timeout value is not a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    Raised when the verify certificate value is not either True or False
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
        self.config_data = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = self.config_data.seed_urls
        self._headers = self.config_data.headers
        self._num_articles = self.config_data.total_articles
        self._encoding = self.config_data.encoding
        self._timeout = self.config_data.timeout
        self._should_verify_certificate = self.config_data.should_verify_certificate
        self._headless_mode = self.config_data.headless_mode

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
        # IncorrectSeedURLError: seed URL does not match standard pattern "https?://w?w?w?."
        if not isinstance(self.config_data.seed_urls, list):
            raise IncorrectSeedURLError
        for seed_url in self.config_data.seed_urls:
            if not re.match(r'^https?://.*', seed_url):
                raise IncorrectSeedURLError

        # NumberOfArticlesOutOfRangeError: total number of articles is out of range from 1 to 150
        # IncorrectNumberOfArticlesError: total number of articles to parse is not integer
        if not isinstance(self.config_data.total_articles, int) \
                or isinstance(self.config_data.total_articles, bool) \
                or not self.config_data.total_articles >= 0:
            raise IncorrectNumberOfArticlesError

        if self.config_data.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        # IncorrectHeadersError: headers are not in a form of dictionary
        if not isinstance(self.config_data.headers, dict):
            raise IncorrectHeadersError

        # IncorrectEncodingError: encoding must be specified as a string
        if not isinstance(self.config_data.encoding, str):
            raise IncorrectEncodingError

        # IncorrectTimeoutError: timeout value must be a positive integer less than 60
        if not isinstance(self.config_data.timeout, int) or not 0 <= self.config_data.timeout <= 60:
            raise IncorrectTimeoutError

        # IncorrectVerifyError: verify certificate value must either be True or False
        if (not isinstance(self.config_data.should_verify_certificate, bool)
                or not isinstance(self.config_data.headless_mode, bool)):
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
    response = requests.get(url, headers=config.get_headers(),
                            timeout=config.get_timeout())
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
        self._config = config
        self.urls = []
        self._seed_urls = self._config.get_seed_urls()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """

        href = article_bs.get('href')
        if href:
            full_url = urljoin('https://www.business-gazeta.ru/', str(href))
            if not urlparse(full_url).scheme:
                full_url = "http://" + full_url
            return full_url
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self._seed_urls:
            response = make_request(seed_url, self._config)
            soup = BeautifulSoup(response.content, "lxml")
            for paragraph in soup.find_all('a', class_="article-news__title"):
                if len(self.urls) >= self._config.get_num_articles():
                    return
                url = self._extract_url(paragraph)
                if not url or url in self.urls:
                    continue
                self.urls.append(url)

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
        self.config = config
        self.full_url = full_url
        self.article_id = article_id
        self.article = Article(url=self.full_url, article_id=self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """

        self.article.title = article_soup.find('h1', {'class': 'article__h1'}).text
        # description = article_soup.find('p', itemprop='description').text
        paragraphs_lst = article_soup.find('div', {'class': 'articleBody'})
        paragraphs = "".join([i.text for i in paragraphs_lst.find_all('p')])
        self.article.text = '. '.join(paragraphs)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        pass

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
        article_bs = BeautifulSoup(response.content, 'lxml')
        self._fill_article_with_text(article_bs)
        self._fill_article_with_meta_information(article_bs)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    # Функция rmtree() модуля shutil рекурсивно удаляет все дерево каталогов.
    # Путь path должен указывать на каталог, но не символическую ссылку на каталог.
    # Функция mkdir() модуля os создает каталог с именем path с режимом доступа к нему mode.
    # Аргумент path может принимать объекты, представляющие путь файловой системы, такие как pathlib.PurePath.
    # The parents=True tells the mkdir command to also create any intermediate parent dirctries that don't already exist
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    prepare_environment(ASSETS_PATH)
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for idx, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=idx, config=configuration)
        parsed_article = parser.parse()
        if isinstance(parsed_article, Article):
            to_raw(parsed_article)
            to_meta(parsed_article)


if __name__ == "__main__":
    main()
