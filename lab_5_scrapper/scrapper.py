"""
Crawler implementation
"""
import time
import requests
import json
import datetime
import re
import os
import shutil

from typing import Pattern, Union
from bs4 import BeautifulSoup
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.safari.options import Options as SafariOptions

from core_utils.article.article import Article
from core_utils.article.io import to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (CRAWLER_CONFIG_PATH,
                                  ASSETS_PATH,
                                  TIMEOUT_LOWER_LIMIT,
                                  TIMEOUT_UPPER_LIMIT)


class IncorrectSeedURLError(Exception):
    """
    Seed URL does not match standard pattern "https?://w?w?w?."
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Total number of articles to parse is not integer
    """


class IncorrectHeadersError(Exception):
    """
    Headers are not in a form of dictionary
    """


class IncorrectEncodingError(Exception):
    """
    Encoding must be specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    Timeout value must be a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    Verify certificate value must either be True or False
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
        self._total_articles = config_dto.total_articles
        self._headers = config_dto.headers
        self._encoding = config_dto.encoding
        self._timeout = config_dto.timeout
        self._verify_certificate = config_dto.should_verify_certificate
        self._headless_mode = config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config) as file:
            config_dto = json.load(file)
        return ConfigDTO(**config_dto)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()

        for url in config_dto.seed_urls:
            if not re.match(r'https?://(www.)?', url):
                raise IncorrectSeedURLError(IncorrectSeedURLError.__doc__.strip())

        if not (isinstance(config_dto.total_articles, int) and
                1 <= config_dto.total_articles <= 150):
            raise NumberOfArticlesOutOfRangeError(NumberOfArticlesOutOfRangeError.__doc__.strip())

        if not (isinstance(config_dto.total_articles, int) and config_dto.total_articles > 0):
            raise IncorrectNumberOfArticlesError(IncorrectNumberOfArticlesError.__doc__.strip())

        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError(IncorrectHeadersError.__doc__.strip())

        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError(IncorrectEncodingError.__doc__.strip())

        if not (isinstance(config_dto.timeout, int) and
                TIMEOUT_LOWER_LIMIT < config_dto.timeout <= TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError(IncorrectTimeoutError.__doc__.strip())

        if not (isinstance(config_dto.should_verify_certificate, bool) and
                isinstance(config_dto.headless_mode, bool)):
            raise IncorrectVerifyError(IncorrectVerifyError.__doc__.strip())

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
        return self._verify_certificate

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
    return requests.get(url=url,
                        headers=config.get_headers(),
                        timeout=config.get_timeout(),
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
        self.driver = webdriver.Safari(options=SafariOptions())

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        try:
            article_href = article_bs.a.get('href')
        except AttributeError:
            pass
        else:
            if isinstance(article_href, str) and article_href.startswith('/doc/'):
                return f'https://www.kommersant.ru{article_href.split("?")[0]}'
            else:
                return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        def scroll_through_page() -> str:
            """
            Uses Selenium to click the button on page
            Returns HTML-code of page with buttons clicked
            """
            self.driver.get(url=url_to_crawl)
            button_xpath = '/html/body/main/div/div/div/div/button'
            button = [button for button in self.driver.find_elements(by=By.XPATH,
                                                                     value=button_xpath)][0]
            iterations = 5
            for i in range(iterations):
                button.click()
                time.sleep(1.5)
            return self.driver.page_source

        for url_to_crawl in self.get_search_urls():
            soup = BeautifulSoup(scroll_through_page(), 'lxml')
            articles_html = soup.find_all('article')

            for article in articles_html:
                result_url = self._extract_url(article)
                if result_url and result_url not in self.urls:
                    self.urls.append(result_url)

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
        self.article = Article(full_url, article_id)
        self.full_url = full_url
        self.article_id = article_id
        self.config = config

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        unformatted_text = article_soup.find('article').find_all('p', class_='doc__text')
        self.article.text = ' '.join(paragraph.text for paragraph in unformatted_text[:-1])

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        article = article_soup.find('article')
        title = article.find('header', class_='doc_header').text.strip()
        self.article.title = title

        author = article.find('p', class_='doc__text document_authors')
        self.article.author.append(author)

        topics = list(theme.text for theme in
                      article.find_all('a', class_='doc_footer__item_name'))
        self.article.topics = topics

        date = article.find('div', class_='doc_header__time').text.strip()
        self.article.date = self.unify_date_format(date)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = requests.get(self.full_url)
        if response.status_code == 200:
            article_bs = BeautifulSoup(response.text, 'lxml')
            self._fill_article_with_text(article_bs)
            self._fill_article_with_meta_information(article_bs)
            return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if os.path.exists(base_path):
        shutil.rmtree(base_path)
    os.makedirs(base_path)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    prepare_environment(ASSETS_PATH)
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)

    crawler = Crawler(config=configuration)
    crawler.find_articles()

    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(url, i, configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)


if __name__ == "__main__":
    main()
