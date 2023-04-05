"""
Crawler implementation
"""
import re
import json
import shutil
import requests

from time import sleep
from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Pattern, Union

from core_utils.article.io import to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import CRAWLER_CONFIG_PATH, ASSETS_PATH
from core_utils.article.article import Article


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
        self.config_dto = self._extract_config_content()
        self._seed_urls = self.get_seed_urls()
        self._num_articles = self.get_num_articles()
        self._headers = self.get_headers()
        self._encoding = self.get_encoding()
        self._timeout = self.get_timeout()
        self._should_verify_certificate = self.get_verify_certificate()

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

        seed_urls = config.get('seed_urls')
        if not isinstance(seed_urls, list) or not all(isinstance(url, str) for url in seed_urls):
            raise IncorrectSeedURLError("Invalid value for seed_urls in configuration file")

        for seed_url in seed_urls:
            if not re.match(r'^https?://w?w?w?.', seed_url):
                raise IncorrectSeedURLError("Invalid seed URL in configuration file")

        total_articles_to_find_and_parse = config.get('total_articles_to_find_and_parse')
        if not isinstance(total_articles_to_find_and_parse, int) or total_articles_to_find_and_parse < 1:
            raise IncorrectNumberOfArticlesError(
                "Invalid value for total_articles_to_find_and_parse in configuration file")

        if total_articles_to_find_and_parse > 150:
            raise NumberOfArticlesOutOfRangeError(
                "Invalid value for total_articles_to_find_and_parse in configuration file")

        headers = config.get('headers', dict)
        if not isinstance(headers, dict):
            raise IncorrectHeadersError("Invalid value for headers in configuration file")

        encoding = config.get('encoding', 'utf-8')
        if not isinstance(encoding, str):
            raise IncorrectEncodingError("Invalid value for encoding in configuration file")

        timeout = config.get('timeout', 10)
        if not isinstance(timeout, int) or timeout < 0 or timeout > 60:
            raise IncorrectTimeoutError("Invalid value for timeout in configuration file")

        should_verify_certificate = config.get('should_verify_certificate', True)
        if not isinstance(should_verify_certificate, bool):
            raise IncorrectVerifyError("Invalid value for should_verify_certificate in configuration file")

        headless_mode = config.get('headless_mode', True)
        if not isinstance(headless_mode, bool):
            raise IncorrectVerifyError("Invalid value for headless_mode in configuration file")

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.config_dto.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.config_dto.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.config_dto.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.config_dto.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.config_dto.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.config_dto.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.config_dto.headless_mode

    @property
    def headers(self):
        return self._headers

    @property
    def seed_urls(self):
        return self._seed_urls


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    sleep(config.get_timeout())
    response = requests.get(url, headers=config.get_headers())
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
            href = link_bs.get('href')
            if href is None:
                continue
            elif href.startswith('https://chelny-izvest.ru/news/') and href.count('/') == 5:
                return href

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self.get_search_urls():
            response = make_request(seed_url, self.config)
            if response.status_code != 200 and response.status_code != 404:
                continue

            article_bs = BeautifulSoup(response.text, 'lxml')
            article_url = self._extract_url(article_bs)
            while len(self.urls) < self.config.get_num_articles():
                self.urls.append(article_url)

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self.config.seed_urls


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
        text_elements = article_soup.find("div", class_="page-main__text").find_all("p")
        self.article.text = "\n".join([p.get_text().strip() for p in text_elements])

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        author_elem = article_soup.find('div', class_='page-main__publish-data').find(
            'a', class_='page-main__publish-author global-link')
        authors = [author_elem.text.strip()] if author_elem else ["NOT FOUND"]

        date_elem = article_soup.find('div', class_='page-main__publish-data').find(
            'a', class_='page-main__publish-date')
        date_str = date_elem.get_text(strip=True) if date_elem else None
        date = self.unify_date_format(date_str)

        category_elem = article_soup.find('div', class_='panel-group').find(
            'a', class_='panel-group__title global-link')
        category = category_elem.get_text(strip=True) if category_elem else None

        title_elem = article_soup.find('div', class_='page-main').find('h1', class_='page-main__head')
        title = title_elem.text.strip() if title_elem else None

        self.article.author = authors
        self.article.date = date
        self.article.category = category
        self.article.title = title

    def unify_date_format(self, date_str: str) -> datetime:
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
        date_format = '%d %B %Y - %H:%M'
        date_str = date_str.replace(date_str.split()[1], months_dict[date_str.split()[1]])
        date_obj = str(datetime.strptime(date_str, date_format))
        formatted_date = datetime.strptime(date_obj, '%Y-%m-%d %H:%M:%S')
        return formatted_date

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        article_soup = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article_soup)
        self._fill_article_with_meta_information(article_soup)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    assets_path = Path(base_path).joinpath(ASSETS_PATH)
    if assets_path.exists() and assets_path.is_dir():
        shutil.rmtree(assets_path)
    assets_path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    pass


if __name__ == "__main__":
    main()
