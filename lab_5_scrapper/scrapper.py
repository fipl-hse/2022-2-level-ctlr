"""
Crawler implementation
"""
from typing import Pattern, Union
import json
from pathlib import Path
from core_utils.config_dto import ConfigDTO
import re
from core_utils.constants import (ASSETS_PATH, CRAWLER_CONFIG_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT,
                                  TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)
import requests
import shutil
import random
import time
from bs4 import BeautifulSoup
from core_utils.article.io import to_raw
from core_utils.article.article import Article
import datetime
from selenium import webdriver


class IncorrectSeedURLError(Exception):
    """
    seed URL does not match standard pattern
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
    encoding must be specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    timeout value must be a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
     verify certificate value must either be True or False
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
        config = self._extract_config_content()
        self._seed_urls = config.seed_urls
        self._num_articles = config.total_articles
        self._headers = config.headers
        self._encoding = config.encoding
        self._timeout = config.timeout
        self._should_verify_certificate = config.should_verify_certificate
        self._headless_mode = config.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return ConfigDTO(**config)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config = self._extract_config_content()

        for url in config.seed_urls:
            if not re.match(re.compile(r"https?://w?."), url):
                raise IncorrectSeedURLError

        if (not isinstance(config.total_articles, int)
                or isinstance(config.total_articles, bool)):
            raise IncorrectNumberOfArticlesError

        if config.total_articles > NUM_ARTICLES_UPPER_LIMIT \
                or config.total_articles < 1:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config.encoding, str):
            raise IncorrectEncodingError

        if config.timeout < TIMEOUT_LOWER_LIMIT or config.timeout > TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError

        if not isinstance(config.should_verify_certificate, bool):
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
    time.sleep(random.randint(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT))
    timeout = config.get_timeout()

    response = requests.get(url, timeout=timeout)
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
        self._seed_url = config.get_seed_urls()
        self._config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        href = article_bs.get('href')
        if href.startswith('/news/') and href.count('/') == 3:
            return href
        return "None"

    def find_articles(self) -> None:
        """
        Finds articles
        """

        for url in self._seed_url:
            driver = webdriver.Chrome(executable_path="C:\\Users\\Ольга\\Desktop\\2022-2-level-ctlr\\chrome "
                                              "driver\\chromedriver_win32\\chromedriver.exe")

            driver.get(url=url)
            last_height = driver.execute_script("return document.body.scrollHeight")

            while len(self.urls) < self._config.get_num_articles():
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(0.5)
                soup = BeautifulSoup(driver.page_source, features="html.parser")
                for elem in soup.find_all('a'):
                    current_url = url + str(self._extract_url(elem))
                    if str(self._extract_url(elem)) != 'None' and len(self.urls) < self._config.get_num_articles() \
                            and current_url not in self.urls:
                        self.urls.append(current_url)

                new_height = driver.execute_script("return document.body.scrollHeight")
                last_height = new_height


    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self.urls


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
        elements = article_soup.find_all("div", class_='mb-[24px] lg:mb-[28px]')
        paragraphs = ""
        for elem in elements:
            par = elem.find_all('p')
            paragraphs += " ".join([text.get_text(strip=True) for text in par])
            paragraphs += " "
        self.article.text = paragraphs

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
        article = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article)
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
    config = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=config)
    crawler.find_articles()
    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=i, config=config)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)


if __name__ == "__main__":
    main()
