"""
Crawler implementation
"""
import json
import requests
import datetime
import re
import os
import shutil
import bs4 as BeautifulSoup
from pathlib import Path
from typing import Pattern, Union
from core_utils.config_dto import ConfigDTO


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
        self.path = path_to_config

        with open(self.path) as j son_file:
            self.content = json.loads(json_file)

        for key, val in self.content.items():
            setattr(self, key, val)

        self.config_obj = self._extract_config_content()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        # with open(self.path) as json_file:
        #     content = json.loads(json_file)

        return ConfigDTO(self.content['seed_urls'],
                         self.content['total_articles_to_find_and_parse'],
                         self.content['headers'],
                         self.content['encoding'],
                         self.content['timeout'],
                         self.content['should_verify_certificate'],
                         self.content['headless_mode'])

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        for element in self.content['seed_urls']:
            if not re.match(r'https://glasnaya.media/\d{4}/\d{2}/\d{2}/\S+[^/]/', element):
                raise IncorrectSeedURLError

        if not isinstance((self.content['total_articles_to_find_and_parse']), int):
            raise IncorrectNumberOfArticlesError

        if self.content['total_articles_to_find_and_parse'] < 1 or self.content['total_articles_to_find_and_parse'] > 150:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(self.content['headers'], dict):
            raise IncorrectHeadersError

        if not isinstance(self.content['encoding'], str):
            raise IncorrectEncodingError

        if self.content['timeout'] <= 0 or self.content['timeout'] > 60:
            raise IncorrectTimeoutError

        if not isinstance(self.content['verify_certificate'], bool):
            raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.config_obj.seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.config_obj.total_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.config_obj.headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.config_obj.encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.config_obj.timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.config_obj.verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.config_obj.headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    config.get_timeout()


class Crawler:
    """
    Crawler implementation
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the Crawler class
        """
        pass

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        pass

    def find_articles(self) -> None:
        """
        Finds articles
        """
        pass

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        pass


class IncorrectSeedURLError(Exception):
    def __init__(self):
        print('Seed URL does not match standard pattern or does not correspond to the target website')


class NumberOfArticlesOutOfRangeError(Exception):
    def __init__(self):
        print('Total number of articles is out of range from 1 to 150')


class IncorrectNumberOfArticlesError(Exception):
    def __init__(self):
        print('Total number of articles to parse is not integer')


class IncorrectHeadersError(Exception):
    def __init__(self):
        print('Headers are not in a form of dictionary')


class IncorrectEncodingError(Exception):
    def __init__(self):
        print('Encoding must be specified as a string')


class IncorrectTimeoutError(Exception):
    def __init__(self):
        print('Timeout value must be a positive integer less than 60')


class IncorrectVerifyError(Exception):
    def __init__(self):
        print('Verify certificate value must either be True or False')


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
    if isinstance(base_path, str):
        way = os.path.join(Path(base_path), 'ASSETS_PATH')
    else:
        way = os.path.join(base_path, 'ASSETS_PATH')

    if os.path.exists(way):
        shutil.rmtree(way)

    os.makedirs(way)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    # YOUR CODE GOES HERE
    pass

if __name__ == "__main__":
    main()
