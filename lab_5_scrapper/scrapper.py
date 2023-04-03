"""
Crawler implementation
"""
from typing import Pattern, Union
from core_utils.config_dto import ConfigDTO
import re
from bs4 import BeautifulSoup
import os
import requests


class IncorrectSeedURLError:
    pass


class NumberOfArticlesOutOfRangeError:
    pass


class IncorrectNumberOfArticlesError:
    pass


class IncorrectHeadersError:
    pass


class IncorrectEncodingError:
    pass


class IncorrectTimeoutError:
    pass


class IncorrectVerifyError:
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
        self.seed_urls = path_to_config.seed_urls
        self.total_articles_to_find_and_parse = path_to_config.total_articles_to_find_and_parse
        self.headers = path_to_config.headers
        self.encoding = path_to_config.encoding
        self.timeout = path_to_config.timeout
        self.verify_certificate = path_to_config.verify_certificate
        self.headless_mode = path_to_config.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        return ConfigDTO(seed_urls=self.seed_urls,
                         total_articles_to_find_and_parse=self.total_articles_to_find_and_parse,
                         headers=self.headers,
                         encoding=self.encoding,
                         timeout=self.timeout,
                         should_verify_certificate=self.verify_certificate,
                         headless_mode=self.headless_mode)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        html_pattern = re.compile(r"https?://w?w?w?")

        for i in self.seed_urls:
            if re.match(html_pattern, i) is None:
                raise IncorrectSeedURLError
            continue

        if self.total_articles_to_find_and_parse > 150 or self.total_articles_to_find_and_parse < 1:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(self.total_articles_to_find_and_parse, int):
            raise IncorrectNumberOfArticlesError

        if not isinstance(self.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(self.encoding, str):
            raise IncorrectEncodingError

        if (self.timeout > 0) and (self.timeout < 60):
            raise IncorrectTimeoutError

        if self.verify_certificate is not bool:
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.total_articles_to_find_and_parse

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    return requests.get(url,
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
        self.url_pattern = 'https://irkutskmedia.ru/news/'
        self.config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        pass

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.config.get_seed_urls():
            self.urls.append(url)

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        pass


class HTMLParser:
    """
    ArticleParser implementation
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initializes an instance of the HTMLParser class
        """
        pass

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        pass

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
        pass


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    if not os.path.exists(base_path):
        os.mkdir(base_path)

    if len(os.listdir(base_path)) != 0:
        os.rmdir(base_path)
        os.mkdir(base_path)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    # YOUR CODE GOES HERE
    pass


if __name__ == "__main__":
    main()
