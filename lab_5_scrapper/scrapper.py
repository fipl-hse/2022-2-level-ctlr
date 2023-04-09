"""
Crawler implementation
"""
import os
import re
import shutil
import json
from typing import Pattern, Union
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from core_utils.config_dto import ConfigDTO
from core_utils.article.article import Article
from core_utils.article.io import to_raw
from core_utils.constants import (ASSETS_PATH, CRAWLER_CONFIG_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT,
                                  TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)
from time import sleep
from random import randint
# from urllib.error import HTTPError


class IncorrectSeedURLError(Exception):
    """Invalid url type"""


class NumberOfArticlesOutOfRangeError(Exception):
    """Incorrect input of articles' number"""


class IncorrectNumberOfArticlesError(Exception):
    """Incorrect type of articles' number"""


class IncorrectHeadersError(Exception):
    """Incorrect type of request's headers"""


class IncorrectEncodingError(Exception):
    """Invalid encoding type"""


class IncorrectTimeoutError(Exception):
    """Timeout number is out of range"""


class IncorrectVerifyError(Exception):
    """verification is not a boolean type"""


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
        self.config_content = self._extract_config_content()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        self._seed_urls = config["seed_urls"]
        self._num_articles = config["total_articles_to_find_and_parse"]
        self._headers = config["headers"]
        self._encoding = config["encoding"]
        self._timeout = config["timeout"]
        self._should_verify_certificate = config["should_verify_certificate"]
        self._headless_mode = config["headless_mode"]
        return ConfigDTO(
            seed_urls=self._seed_urls,
            total_articles_to_find_and_parse=self._num_articles,
            headers=self._headers,
            encoding=self._encoding,
            timeout=self._timeout,
            should_verify_certificate=self._should_verify_certificate,
            headless_mode=self._headless_mode,
        )

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self.path_to_config, "r", encoding="utf-8") as f:
            config = json.load(f)

        seed_urls = config["seed_urls"]
        headers = config["headers"]
        total_articles_to_find_and_parse = config["total_articles_to_find_and_parse"]
        encoding = config["encoding"]
        timeout = config["timeout"]
        verify_certificate = config["should_verify_certificate"]
        headless_mode = config['headless_mode']

        if not isinstance(seed_urls, list):
            raise IncorrectSeedURLError

        for url in seed_urls:
            if not re.match(r"https?://w?w?w?.", url) or not isinstance(url, str):
                raise IncorrectSeedURLError

        if not 1 < total_articles_to_find_and_parse < NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if (
                not isinstance(total_articles_to_find_and_parse, int)
        ):
            raise IncorrectNumberOfArticlesError

        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        if (not isinstance(timeout, int)
                or not TIMEOUT_LOWER_LIMIT < timeout < TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError

        if not isinstance(verify_certificate, bool) or not isinstance(headless_mode, bool):
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

    def seed_urls(self):
        return self._seed_urls


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    sleep_time = randint(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)
    sleep(sleep_time)
    return requests.get(
        url,
        headers=config.get_headers(),
        timeout=config.get_timeout(),
        verify=config.get_verify_certificate(),
    )


class Crawler:
    """
    Crawler implementation
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the Crawler class
        """
        self.url_pattern = "https://irkutskmedia.ru/news/"
        self.config = config
        self.urls = []

    @staticmethod
    def _extract_url(article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        all_tags_bs = article_bs.find_all("a", string=re.compile(r'https://irkutskmedia\.ru/news/.'))
        for tag in all_tags_bs:
            return tag.get("href")

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for url in self.get_search_urls():
            # makes a get-response to a server
            response = make_request(url=url, config=self.config)
            if response.status_code != 200 or response.status_code == 404:
                continue
            # gets html page
            main_bs = BeautifulSoup(response.text, "lxml")
            link = self._extract_url(main_bs)
            self.urls.append(link)

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
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        text = article_soup.text
        # break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # drop blank lines
        text = "\n".join(chunk for chunk in chunks if chunk)
        self.article.text = text

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        pass

    def unify_date_format(self, date_str: str):
        """
        Unifies date format
        """
        pass

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config).text
        self._fill_article_with_text(BeautifulSoup(response, "lxml"))
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    project_path = Path(__file__).parent.parent / base_path

    # checks if the directory exists
    if not project_path.exists():
        # if it doesn't, directory is created
        project_path.mkdir(parents=True)

    else:
        # if the directory exists, nested files are checked
        for dirpath, dirnames, files in os.walk(project_path):
            # if the directory has a nested directories or files, the program removes the folder
            if dirpath or files or dirnames:
                shutil.rmtree(project_path)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()

    for identification, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(
            full_url=url, article_id=identification, config=configuration
        )
        article = parser.parse()
        to_raw(article)


if __name__ == "__main__":
    main()
