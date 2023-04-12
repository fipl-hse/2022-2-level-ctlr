"""
Crawler implementation
"""
import datetime
import json
import random
import re
import shutil
import time
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
    Seed URL does not match standard pattern or does not correspond to the target website
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles is out of the needed range
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
    Incorrect timeout value
    """


class IncorrectVerifyError(Exception):
    """
    Incorrect verify certificate value
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
        dto = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = dto.seed_urls
        self._num_articles = dto.total_articles
        self._headers = dto.headers
        self._encoding = dto.encoding
        self._timeout = dto.timeout
        self._should_verify_certificate = dto.should_verify_certificate
        self._headless_mode = dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as file:
            parameters = json.load(file)
        return ConfigDTO(**parameters)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        dto = self._extract_config_content()

        if not dto.seed_urls or not isinstance(dto.seed_urls, list):
            raise IncorrectSeedURLError("Invalid value for seed_urls")

        for url in dto.seed_urls:
            if not isinstance(url, str) or not re.match(r'^https?://.*/', url):
                raise IncorrectSeedURLError("Invalid seed url")

        if (not isinstance(dto.total_articles, int)
                or isinstance(dto.total_articles, bool)
                or dto.total_articles < 1):
            raise IncorrectNumberOfArticlesError(
                "Invalid value for total_articles_to_find_and_parse")

        if dto.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError(
                "Invalid value for total_articles_to_find_and_parse")

        if not isinstance(dto.headers, dict):
            raise IncorrectHeadersError("Invalid value for headers")

        if not isinstance(dto.encoding, str):
            raise IncorrectEncodingError("Invalid value for encoding")

        if not isinstance(dto.timeout, int) or dto.timeout < TIMEOUT_LOWER_LIMIT or \
                dto.timeout > TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError("Invalid value for timeout")

        if not isinstance(dto.should_verify_certificate, bool) or \
                not isinstance(dto.headless_mode, bool):
            raise IncorrectVerifyError(
                "Invalid value for should_verify_certificate or headless_mode")

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
    time.sleep(random.randrange(1, 8))
    response = requests.get(url, headers=config.get_headers(), timeout=config.get_timeout(),
                            verify=config.get_verify_certificate())
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
        self.urls = []
        self.config = config
        self.seed_urls = config.get_seed_urls()
        self.number_of_articles = config.get_num_articles()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        href = article_bs.get('href')
        if isinstance(href, str) and href.startswith('/news/') \
                and len(re.findall('[0-9]', href)) >= 8:
            return "https://livennov.ru" + href
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for link in self.seed_urls:
            response = make_request(link, self.config)
            main_bs = BeautifulSoup(response.text, 'lxml')
            url = self._extract_url(main_bs)
            if len(self.urls) >= self.config.get_num_articles():
                return
            if not url:
                continue
            if url not in self.seed_urls:
                self.urls.append(url)

        # for link in self.seed_urls:
        #     response = make_request(link, self.config)
        #     links_bs = BeautifulSoup(response.text, 'lxml').find_all('a')
        #     for link_bs in links_bs:
        #         url = self._extract_url(link_bs)
        #         if not url:
        #             continue
        #         if url not in self.seed_urls:
        #             self.urls.append(url)
        #         if len(self.urls) >= self.config.get_num_articles():
        #             return

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
        self.full_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        main_text = article_soup.find('div', {
            'itemprop': 'articleBody'}).text.replace('\n\n', ' ').replace('  ', '').strip()
        self.article.text = main_text

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title_info = article_soup.find('div', {'class', 'b-news-detail-top'}).find('h1').text
        self.article.title = title_info

        author_info = article_soup.find('div', itemprop="author")
        if author_info:
            self.article.author.append(author_info.get_text(strip=True))
        else:
            self.article.author.append('NOT FOUND')

        date_info = article_soup.find('time', {'class': "b-meta-item"}).get_text(strip=True)
        self.article.date = self.unify_date_format(date_info)

        topics_info = [topic.get_text(strip=True)
                       for topic in article_soup.find_all('div', {'class': "lid-detail"})
                       if topic.get_text(strip=True)]
        self.article.topics = topics_info

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%d.%m.%Y %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        main_bs = BeautifulSoup(response.content, "lxml")
        self._fill_article_with_text(main_bs)
        self._fill_article_with_meta_information(main_bs)
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
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=url, article_id=i, config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
