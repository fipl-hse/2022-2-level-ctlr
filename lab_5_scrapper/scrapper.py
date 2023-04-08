"""
Crawler implementation
"""
import re
import os
import requests
import shutil
import json

from typing import Pattern, Union
from bs4 import BeautifulSoup
from pathlib import Path

from core_utils.config_dto import ConfigDTO
from core_utils.constants import CRAWLER_CONFIG_PATH, ASSETS_PATH
from core_utils.article.article import Article
from core_utils.article.io import to_raw


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
        self._extract_config_content()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self._seed_urls = config['seed_urls']
        self._total_articles_to_find_and_parse = config['total_articles_to_find_and_parse']
        self._headers = config['headers']
        self._encoding = config['encoding']
        self._timeout = config['timeout']
        self._verify_certificate = config['should_verify_certificate']
        self._headless_mode = config['headless_mode']
        return ConfigDTO(seed_urls=self._seed_urls,
                         total_articles_to_find_and_parse=self._total_articles_to_find_and_parse,
                         headers=self._headers,
                         encoding=self._encoding,
                         timeout=self._timeout,
                         should_verify_certificate=self._verify_certificate,
                         headless_mode=self._headless_mode)

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
        verify_certificate = config['should_verify_certificate']
        # headless_mode = config['headless_mode']

        html_pattern = re.compile(r"https?://w?w?w?.")

        for i in seed_urls:
            if re.match(html_pattern, i) is None:
                raise IncorrectSeedURLError
            continue

        if total_articles_to_find_and_parse > 150 or total_articles_to_find_and_parse < 1:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(total_articles_to_find_and_parse, int):
            raise IncorrectNumberOfArticlesError

        if not isinstance(headers, dict):
            raise IncorrectHeadersError

        if not isinstance(encoding, str):
            raise IncorrectEncodingError

        if (timeout < 0) and (timeout > 60):
            raise IncorrectTimeoutError

        if not isinstance(verify_certificate, bool):
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
        return self._total_articles_to_find_and_parse

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

    @staticmethod
    def _extract_url(article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        return article_bs.get('href')

    def find_articles(self) -> None:
        """
        Finds articles
        """
        # makes a get-response to a server
        response = make_request(self.url_pattern, self.config)
        # gets html page
        main_bs = BeautifulSoup(response.text, 'lxml')
        # extracts appropriate urls and adds them to seed
        all_tags_bs = main_bs.find_all("a", string=re.compile(r'\bhttps?\b'))
        for tag in all_tags_bs:
            clean_link = self._extract_url(tag)
            self.urls.append(clean_link)

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
        self._article = Article(self.full_url, self.article_id)

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
        text = '\n'.join(chunk for chunk in chunks if chunk)
        self._article.text = text

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
        self._fill_article_with_text(BeautifulSoup(response, 'lxml'))
        return self._article


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

    for identification, url in enumerate(crawler.urls):
        parser = HTMLParser(full_url=url,
                            article_id=identification,
                            config=configuration)
        article = parser.parse()
        to_raw(article)


if __name__ == "__main__":
    main()
