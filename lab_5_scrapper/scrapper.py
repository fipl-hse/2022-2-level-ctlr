"""
Crawler implementation
"""
import datetime
import json
import re
import shutil
from pathlib import Path
from typing import Pattern, Union
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_meta, to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH


class IncorrectSeedURLError(Exception):
    """Raised when the seed URL does not match the
    standard pattern or does not correspond to the target website"""


class NumberOfArticlesOutOfRangeError(Exception):
    """Raised when the total number of articles is out of range from 1 to 150"""


class IncorrectNumberOfArticlesError(Exception):
    """Raised when the total number of articles to parse is not an integer"""


class IncorrectHeadersError(Exception):
    """Raised when headers are not in the form of a dictionary"""


class IncorrectEncodingError(Exception):
    """Raised when the encoding is not specified as a string"""


class IncorrectTimeoutError(Exception):
    """Raised when the timeout value is not a positive integer less than 60"""


class IncorrectVerifyError(Exception):
    """Raised when the verify certificate value is not either True or False"""



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
        self.config_data = self._extract_config_content()
        self._seed_urls = self.config_data.seed_urls
        self._num_articles = self.config_data.total_articles
        self._headers = self.config_data.headers
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
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

        seed_urls = config['seed_urls']
        headers = config['headers']
        total_articles_to_find_and_parse = config['total_articles_to_find_and_parse']
        encoding = config['encoding']
        timeout = config['timeout']
        should_verify_certificate = config['should_verify_certificate']
        headless_mode = config['headless_mode']

        correct_url = 'https://dzer.ru/'
        if not isinstance(seed_urls, list) or not all(isinstance(url, str) for url in seed_urls):
            raise IncorrectSeedURLError("Invalid value for seed_urls in configuration file")
        for seed_url in seed_urls:
            if not re.match(r'^https?://w?w?w?.', seed_url) \
                    and seed_url.split('/')[:2] != correct_url.split('/')[:2]:
                raise IncorrectSeedURLError(
    "Invalid seed URL in configuration file"
    )

        if not isinstance(total_articles_to_find_and_parse, int) \
                or total_articles_to_find_and_parse < 1:
            raise IncorrectNumberOfArticlesError(
                "Invalid value for total_articles_to_find_and_parse in configuration file")

        if total_articles_to_find_and_parse > 150:
            raise NumberOfArticlesOutOfRangeError(
                "Invalid value for total_articles_to_find_and_parse in configuration file")

        if not isinstance(headers, dict):
            raise IncorrectHeadersError("Invalid value for headers in configuration file")

        if not isinstance(encoding, str):
            raise IncorrectEncodingError("Invalid value for encoding in configuration file")

        if not isinstance(timeout, int) or timeout < 1 or timeout > 60:
            raise IncorrectTimeoutError(
                "Invalid value for timeout in configuration file"
                )

        if not isinstance(should_verify_certificate, bool):
            raise IncorrectVerifyError(
        "Invalid value for should_verify_certificate in configuration file"
        )

        if not isinstance(headless_mode, bool):
            raise IncorrectVerifyError(
        "Invalid value for headless_mode in configuration file"
        )


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
    headers = config.get_headers()
    timeout = config.get_timeout()
    verify = config.get_verify_certificate()

    response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
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
        self.seed_urls = config.get_seed_urls()
        self.config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        current_url = article_bs.find('meta', property='og:url').get('content')
        for link in article_bs.find_all('a',
                                        class_=lambda value: value and ('mininews' in
                                        value or 'midinews' in value)):
            href = link.get('href') or ''
            if href:
                return urljoin(str(current_url), str(href))
        return urljoin(str(current_url), '')

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self.seed_urls:
            response = make_request(seed_url, self.config)
            if response.status_code == 200:
                html = response.text
                main_bs = BeautifulSoup(html, 'html.parser')
                urls = self._extract_url(main_bs)
                self.urls.append(urls)
                if len(self.urls) >= self.config.get_num_articles():
                    return

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
        self.article_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(self.article_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        text_elements = article_soup.find_all(
            "div", class_="article__paragraph article__paragraph_second"
        )
        text_list = [element.get_text(strip=True) for element in text_elements]
        text = "\n".join(text_list)
        self.article.text = text

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title_tag = article_soup.find_all('h1', {'class': 'article__title'})[0]
        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            title =  "NOT FOUND"
        self.article.title = title

        author_tag = article_soup.find_all('p', {'class': 'article__prepared'})
        if author_tag:
            authors = author_tag[0].get_text(strip=True)
        else:
            authors = ["NOT FOUND"]
        self.article.author = authors

        topic_tag = article_soup.find('div', {'class': 'article__category'}).find('a')
        if topic_tag:
            topic = topic_tag.get_text(strip=True)
        else:
            topic = "NOT FOUND"
        self.article.topic = topic

        date_tag = article_soup.find('div', {'class': 'article__date'})
        if date_tag:
            date_str = date_tag.get_text(strip=True)
        else:
            date_str = "NOT FOUND"
        date = self.unify_date_format(date_str)
        if date:
            self.article.date = date
        else:
            self.article.date = datetime.datetime.now()


    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        months = {
            "января": "january",
            "февраля": "february",
            "марта": "march",
            "апреля": "april",
            "мая": "may",
            "июня": "june",
            "июля": "july",
            "августа": "august",
            "сентября": "september",
            "октября": "october",
            "ноября": "november",
            "декабря": "december"
        }
        for rus_month, en_month in months.items():
            date_str = date_str.replace(rus_month, en_month)
        try:
            return datetime.datetime.strptime(date_str, '%H:%M, %d %b %Y')
        except ValueError:
            return None



    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.article_url, self.config)
        article_soup = BeautifulSoup(response.text, 'html.parser')
        self._fill_article_with_text(article_soup)
        self._fill_article_with_meta_information(article_soup)
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
            to_meta(article)




if __name__ == "__main__":
    main()
