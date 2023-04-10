"""
Crawler implementation
"""
import json
import re
import shutil
import requests
import datetime
from typing import Pattern, Union
from core_utils.config_dto import ConfigDTO
from pathlib import Path
from bs4 import BeautifulSoup
from core_utils.article.article import Article
from core_utils.article.io import to_raw
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH


class IncorrectSeedURLError(Exception):
    """
    Seed URL does not match standard pattern
    """
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of range from 1 to 150
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
    Timeout value must be a positive integer less than 60
    """
    pass


class IncorrectVerifyError(Exception):
    """
    Verify certificate value must either be True or False
    """
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
        self.config_content = self._extract_config_content()
        self._seed_urls = self.config_content.seed_urls
        self._num_articles = self.config_content.total_articles
        self._headers = self.config_content.headers
        self._encoding = self.config_content.encoding
        self._timeout = self.config_content.timeout
        self._should_verify_certificate = self.config_content.should_verify_certificate
        self._headless_mode = self.config_content.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config_data = json.load(file)
        return ConfigDTO(**config_data)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            config_data = json.load(file)

        seed_urls = config_data.get('seed_urls')
        headers = config_data.get('headers')
        total_articles_to_find_and_parse = config_data.get('total_articles_to_find_and_parse')
        encoding = config_data.get('encoding')
        timeout = config_data.get('timeout')
        should_verify_certificate = config_data.get('should_should_verify_certificate')
        headless_mode = config_data.get('headless_mode')

        if not isinstance(seed_urls, list):
            raise IncorrectSeedURLError

        for seed_url in seed_urls:
            if not re.match(r'https?://w?w?w?.', seed_url):
                raise IncorrectSeedURLError

        if not isinstance(total_articles_to_find_and_parse, int) or isinstance(
                total_articles_to_find_and_parse, bool) \
                or total_articles_to_find_and_parse < 0:
            raise IncorrectNumberOfArticlesError

        if total_articles_to_find_and_parse < 1 or total_articles_to_find_and_parse > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        if not isinstance(timeout, int) or timeout < 1 or timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(should_verify_certificate, bool) or not isinstance(headless_mode, bool):
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.config_content.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.config_content.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.config_content.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.config_content.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.config_content.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.config_content.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.config_content.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
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
        self._config = config
        self._seed_urls = config.get_seed_urls()
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if isinstance(url, str) and url.startswith('https://kazanfirst.ru/news/') and len(url) > 27:
            return url

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self._seed_urls:
            response = make_request(seed_url, self._config)
            if response.status_code != 200:
                continue
            else:
                article_bs = BeautifulSoup(response.text, 'lxml')
                pages = article_bs.find_all(
                    'a', {'class': 'post-block-item  post-item column-list__item js-column-item'})
                for page in pages:
                    url = self._extract_url(page)
                    self.urls.append(url)
                    if len(self.urls) >= self._config.get_num_articles():
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
        self.config = config
        self.article = Article(full_url, article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        article_text = article_soup.find('section', {'id': 'redactor-content'})
        all_paragraphs = article_text.find_all('p')
        paragraphs_text = []
        for paragraph in all_paragraphs[:-1]:
            paragraphs_text.append(paragraph)
        self.article.text = '\n'.join(paragraphs_text)

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
        article_bs = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article_bs)
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
    prepare_environment(ASSETS_PATH)
    config = Config(CRAWLER_CONFIG_PATH)
    crawler = Crawler(config)
    crawler.find_articles()
    for i, full_url in enumerate(crawler.urls, 1):
        parser = HTMLParser(full_url=full_url, article_id=i, config=config)
        article = parser.parse()
        to_raw(article)


if __name__ == "__main__":
    main()
