"""
Crawler implementation
"""
import datetime
import json
import re
import shutil
from pathlib import Path
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_meta, to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (ASSETS_PATH, CRAWLER_CONFIG_PATH,
                                  NUM_ARTICLES_UPPER_LIMIT,
                                  TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT)


class IncorrectSeedURLError(Exception):
    """
    Seed URL does not match standard pattern
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
        self._config_dto = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = self._config_dto.seed_urls
        self._num_articles = self._config_dto.total_articles
        self._headers = self._config_dto.headers
        self._encoding = self._config_dto.encoding
        self._timeout = self._config_dto.timeout
        self._should_verify_certificate = self._config_dto.should_verify_certificate
        self._headless_mode = self._config_dto.headless_mode


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
        config_dto = self._extract_config_content()

        if not isinstance(config_dto.seed_urls, list):
            raise IncorrectSeedURLError

        if config_dto.seed_urls:
            for url in config_dto.seed_urls:
                if not isinstance(url, str) or not re.match("https?://.*/", url):
                    raise IncorrectSeedURLError
        else:
            raise IncorrectSeedURLError

        if (not isinstance(config_dto.total_articles, int)
            or isinstance(config_dto.total_articles, bool)
               or config_dto.total_articles < 1):
            raise IncorrectNumberOfArticlesError

        if config_dto.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError

        if (not isinstance(config_dto.timeout, int) or config_dto.timeout < TIMEOUT_LOWER_LIMIT
            or config_dto.timeout > TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError

        if not isinstance(config_dto.should_verify_certificate, bool) \
                or not isinstance(config_dto.headless_mode, bool):
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
    headers = config.get_headers()
    timeout = config.get_timeout()
    verify = config.get_verify_certificate()
    response = requests.get(url, headers=headers, timeout=timeout, verify=verify)
    response.encoding = config.get_encoding()
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
        self._config = config
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        url = article_bs.get('href')
        if isinstance(url, str) and url.startswith('https://abnews.ru/'):
            return url
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self._config.get_seed_urls():
            response = make_request(seed_url, self._config)
            if response.status_code == 200:
                main_bs = BeautifulSoup(response.text, 'lxml')
                all_articles = main_bs.find("div", class_="sidebar-news-list")
                if all_articles:
                    all_links = all_articles.find_all("a")
                    for link in all_links:
                        if len(self.urls) >= self._config.get_num_articles():
                            break
                        url = self._extract_url(link)
                        if url is None:
                            continue
                        if url and url not in self.urls:
                            self.urls.append(url)




    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._config.get_seed_urls()


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
        article_text = article_soup.find('div', class_='article-text')
        all_paragraphs = article_text.find_all('p')
        par_text = [p.text.strip() for p in all_paragraphs]
        self.article.text += '\n'.join(par_text)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        self.article.title = article_soup.find('h1').text
        tag_authors = article_soup.find('span', class_='author-post')
        authors = [name.text.strip() for name in tag_authors if tag_authors]
        if authors[1]:
            self.article.author = authors[1:]
        else:
            self.article.author = ['NOT FOUND']

        topics = [title.text for title in article_soup.find_all('a', class_='tags-link')]
        self.article.topics = topics

        date = article_soup.find('div', class_='article-info-item')
        string_date = date.text
        self.article.date = self.unify_date_format(string_date)

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        list_date = date_str.lower().split()

        months_collection = {"января": "01", "февраля": "02", "марта": "03",
                             "апреля": "04", "мая": "05", "июня": "06",
                             "июля": "07", "августа": "08", "сентября": "09",
                             "октября": "10", "ноября": "11", "декабря": "12"}
        year = ''
        month = ''
        day = ''
        time = ''

        for element in list_date:
            if ':' in element:
                time += element[:5]
            if element in months_collection:
                month += months_collection[element]
            digits = ['1', '2', '3', '4', '5', '6', '7', '8', '9']
            years = ['2020', '2021', '2022', '2023']
            if element.isdigit() and element in digits:
                day += '0' + element
            if element.isdigit() and element not in digits and element not in years:
                day += element
            if element.isdigit() and element in years:
                year += element

        correct_date = year + month + day + time
        return datetime.datetime.strptime(correct_date, '%Y%m%d%H:%M')


    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        articles = BeautifulSoup(response.content, "lxml")
        self._fill_article_with_text(articles)
        self._fill_article_with_meta_information(articles)
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
    # YOUR CODE GOES HERE
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(configuration)
    crawler.find_articles()
    for idx, url in enumerate(crawler.urls):
        parser = HTMLParser(url, idx+1, configuration)
        text = parser.parse()
        if isinstance(text, Article):
            to_raw(text)
            to_meta(text)


if __name__ == "__main__":
    main()
