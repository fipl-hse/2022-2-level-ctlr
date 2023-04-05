"""
Crawler implementation
"""
from bs4 import BeautifulSoup
from typing import Pattern, Union
import datetime
from core_utils.article.article import Article
import re
from urllib.parse import urljoin
from pathlib import Path
import shutil
import requests
from core_utils.config_dto import ConfigDTO
import json



class IncorrectSeedURLError(Exception):
    """Raised when the seed URL does not match the standard pattern or does not correspond to the target website"""
    pass

class NumberOfArticlesOutOfRangeError(Exception):
    """Raised when the total number of articles is out of range from 1 to 150"""
    pass

class IncorrectNumberOfArticlesError(Exception):
    """Raised when the total number of articles to parse is not an integer"""
    pass

class IncorrectHeadersError(Exception):
    """Raised when headers are not in the form of a dictionary"""
    pass

class IncorrectEncodingError(Exception):
    """Raised when the encoding is not specified as a string"""
    pass

class IncorrectTimeoutError(Exception):
    """Raised when the timeout value is not a positive integer less than 60"""
    pass

class IncorrectVerifyError(Exception):
    """Raised when the verify certificate value is not either True or False"""
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
        self.config_data = self._extract_config_content()
        self._seed_urls = self.get_seed_urls()
        self._num_articles = self.get_num_articles()
        self._headers = self.get_headers()
        self._encoding = self.get_encoding()
        self._timeout = self.get_timeout()
        self._should_verify_certificate = self.get_verify_certificate()
        self._headless_mode = self.get_headless_mode()

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

        headers = config.get('headers', {})
        if not isinstance(headers, dict):
            raise IncorrectHeadersError("Invalid value for headers in configuration file")

        encoding = config.get('encoding', 'utf-8')
        if not isinstance(encoding, str):
            raise IncorrectEncodingError("Invalid value for encoding in configuration file")

        timeout = config.get('timeout', 5)
        if not isinstance(timeout, int) or timeout < 1 or timeout > 60:
            raise IncorrectTimeoutError("Invalid value for timeout in configuration file")

        should_verify_certificate = config.get('should_verify_certificate', bool)
        if not isinstance(should_verify_certificate, bool):
            raise IncorrectVerifyError("Invalid value for should_verify_certificate in configuration file")

        headless_mode = config.get('headless_mode', True)
        if not isinstance(headless_mode, bool):
            raise IncorrectVerifyError("Invalid value for headless_mode in configuration file")


    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.config_data.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.config_data.total_articles


    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.config_data.headers


    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.config_data.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.config_data.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.config_data.should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.config_data.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    headers = config.get_headers()
    timeout = config.get_timeout()
    verify = config.get_verify_certificate()

    response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    response.raise_for_status()
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
        current_url = article_bs.find('meta', property='og:url').get('content')
        for link in article_bs.find_all('a',
                                        class_=lambda value: value and ('mininews' in value or 'midinews' in value)):
            href = link.get('href')
            if href:
                abs_href = urljoin(current_url, href)
                return abs_href
        return None

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self.get_search_urls():
            response = make_request(seed_url, self.config)
            if response.status_code == 200:
                html = response.text
                main_bs = BeautifulSoup(html, 'html.parser')
                urls = self._extract_url(main_bs)
                self.urls.append(urls)
            else:
                continue

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
        self.article_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(full_url, article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        article_text = ""
        paragraphs = article_soup.find_all("div", class_="article__paragraph")
        for p in paragraphs:
            texts = p.find_all("p")
            for text in texts:
                article_text += text.text.strip() + " "
        self.text = article_text.strip()

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
        response = requests.get(self.article_url)
        response.raise_for_status()
        article_bs = BeautifulSoup(response.text, 'html.parser')
        self._fill_article_with_text(article_bs)

        return self.article



def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    base_path = Path(base_path)

    if base_path.exists() and any(base_path.iterdir()):
        shutil.rmtree(base_path)

    base_path.mkdir(parents=True, exist_ok=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    pass


if __name__ == "__main__":
    main()
