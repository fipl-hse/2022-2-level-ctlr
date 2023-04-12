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
from core_utils.constants import CRAWLER_CONFIG_PATH, ASSETS_PATH


class IncorrectSeedURLError(Exception):
    """
    Incorrect seed URl
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Number Of Articles Out Of Range
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Incorrect Number Of Articles Error
    """


class IncorrectHeadersError(Exception):
    """
    Incorrect Headers Error
    """


class IncorrectEncodingError(Exception):
    """
    Incorrect Encoding Error
    """


class IncorrectTimeoutError(Exception):
    """
    Incorrect Timeout Error
    """


class IncorrectVerifyError(Exception):
    """
    Incorrect Verify Error
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
        with open(self.path_to_config, "r") as f:
            loaded = json.load(f)
        return ConfigDTO(**loaded)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        configdto = self._extract_config_content()
        if not isinstance(configdto.seed_urls, list):
            raise IncorrectSeedURLError
        for seedurl in configdto.seed_urls:
            if not re.match(r"https?://w?w?w?.", seedurl):
                raise IncorrectSeedURLError

        if not isinstance(configdto.total_articles, int) or configdto.total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if configdto.total_articles > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(configdto.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(configdto.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(configdto.timeout, int) or configdto.timeout < 0 or configdto.timeout > 60:
            raise IncorrectTimeoutError

        if not isinstance(configdto.should_verify_certificate, bool) or not isinstance(configdto.headless_mode, bool):
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
    return requests.get(url, timeout=config.get_timeout(), headers=config.get_headers(),
                        verify=config.get_verify_certificate())


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
        return "https://newsroom24.ru" + article_bs.find("a").get("href")

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self.config.get_seed_urls():
            response = make_request(seed_url, self.config)
            bs = BeautifulSoup(response.text, 'lxml')
            for link in bs.find_all("div", class_="data"):
                url = self._extract_url(link)
                if url not in self.urls:
                    self.urls.append(url)
                if len(self.urls) >= self.config.get_num_articles():
                    return

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
        self.article = Article(url=full_url, article_id=article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        text_block = article_soup.find("div", class_="main_text_ip")
        paragraphs = text_block.find_all("p")
        self.article.text = " ".join(paragraph.text.strip() for paragraph in paragraphs)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        self.article.author = ["NOT FOUND"]
        self.article.topics = [article_soup.find("div", class_="tag").text]
        # self.article.date = self.unify_date_format(article_soup.find("div", class_="date").get_text())
        self.article.title = article_soup.find("h1").text

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%d.%m.%Y %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        article_bs = BeautifulSoup(response.text, 'lxml')
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
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, full_url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=full_url, article_id=i, config=configuration)
        article = parser.parse()
        to_raw(article)
        to_meta(article)


if __name__ == "__main__":
    main()
