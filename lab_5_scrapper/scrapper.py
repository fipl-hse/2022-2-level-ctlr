"""
Crawler implementation
"""
from typing import Pattern, Union
from core_utils.config_dto import ConfigDTO
import re
from bs4 import BeautifulSoup
import os
import requests
from pathlib import Path
import shutil
import json
from core_utils.article.article import Article


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

    def __init__(self, path_to_config: Path) -> None:
        """
        Initializes an instance of the Config class
        """
        with open(path_to_config, 'r') as f:
            config = json.load(f)
            self._seed_urls = config['seed_urls']
            self._total_articles_to_find_and_parse = config['total_articles_to_find_and_parse']
            self._headers = config['headers']
            self._encoding = config['encoding']
            self._timeout = config['timeout']
            self._verify_certificate = config['verify_certificate']
            self._headless_mode = config['headless_mode']

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
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
        html_pattern = re.compile(r"https?://w?w?w?.")

        for i in self._seed_urls:
            if re.match(html_pattern, i) is None:
                raise IncorrectSeedURLError
            continue

        if self._total_articles_to_find_and_parse > 150 or self._total_articles_to_find_and_parse < 1:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(self._total_articles_to_find_and_parse, int):
            raise IncorrectNumberOfArticlesError

        if not isinstance(self._headers, dict):
            raise IncorrectHeadersError

        if not isinstance(self._encoding, str):
            raise IncorrectEncodingError

        if (self._timeout > 0) and (self._timeout < 60):
            raise IncorrectTimeoutError

        if self._verify_certificate is not bool:
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
        self._urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        # using regex in string argument allows us to find only absolute links
        # and return a list with them
        return article_bs.find_all("a", string=re.compile(r'\bhttps?\b')).get('href')

    def find_articles(self) -> None:
        """
        Finds articles
        """
        # makes a get-response to a server
        response = make_request(self.url_pattern, self._config)
        # gets html page
        main_bs = BeautifulSoup(response.text, 'lxml')
        # extracts appropriate urls and adds them to seed
        for url in self._extract_url(main_bs):
            self._urls.append(url)

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._urls


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

    def unify_date_format(self, date_str: str) -> datetime.datetime:
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
            if files or dirnames:
                shutil.rmtree(project_path)
        # an empty folder is created
        project_path.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    pass


if __name__ == "__main__":
    main()
