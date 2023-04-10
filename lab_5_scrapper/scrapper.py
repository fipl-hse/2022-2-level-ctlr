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
from typing import Union

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


class IncorrectNumberOfArticlesError(Exception):
    """
    Inappropriate value for number of articles
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    total number of articles is out of range from 1 to 150
    """


class IncorrectHeadersError(Exception):
    """
    headers are not in a form of dictionary
    """


class IncorrectEncodingError(Exception):
    """
    encoding must be specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    timeout value must be a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    verify certificate value must either be `True` or `False`
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
        self._validate_config_content()
        config_dto = self._extract_config_content()
        self._seed_urls = config_dto.seed_urls
        self._num_articles = config_dto.total_articles
        self._headers = config_dto.headers
        self._encoding = config_dto.encoding
        self._timeout = config_dto.timeout
        self._should_verify_certificate = config_dto.should_verify_certificate
        self._headless_mode = config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return ConfigDTO(
            seed_urls=config['seed_urls'],
            total_articles_to_find_and_parse=config['total_articles_to_find_and_parse'],
            headers=config['headers'],
            encoding=config['encoding'],
            timeout=config['timeout'],
            should_verify_certificate=config['should_verify_certificate'],
            headless_mode=config['headless_mode']
        )

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()

        if not isinstance(config_dto.seed_urls, list):
            raise IncorrectSeedURLError

        for url in config_dto.seed_urls:
            if not isinstance(url, str) or not re.match(r'https?://.*/', url):
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

        if (not isinstance(config_dto.timeout, int)
                or config_dto.timeout < TIMEOUT_LOWER_LIMIT
                or config_dto.timeout > TIMEOUT_UPPER_LIMIT):
            raise IncorrectTimeoutError

        if (not isinstance(config_dto.should_verify_certificate, bool)
                or not isinstance(config_dto.headless_mode, bool)):
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
    time.sleep(random.uniform(1.1, 2.2))
    proxy_ip = '68.188.59.198:80'
    proxy = {'http': proxy_ip}
    response = requests.get(url, headers=config.get_headers(), timeout=config.get_timeout(),
                            verify=config.get_verify_certificate(), proxies=proxy)
    response.encoding = response.apparent_encoding
    return response


def is_article(url: str) -> bool:
    """
    /photo/ and /tests/ are not articles
    """
    return '/articles/photo/' not in url and '/tests/' not in url


class Crawler:
    """
    Crawler implementation
    """
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
        return 'https://econs.online' + str(article_bs.a.get('href'))

    def find_articles(self) -> None:
        """
        Finds articles
        """
        count_urls = 0
        while count_urls < self.config.get_num_articles():
            for url in self.get_search_urls():
                try:
                    response = make_request(url=url, config=self.config)
                    response.raise_for_status()
                except requests.exceptions.HTTPError:
                    continue
                soup = BeautifulSoup(response.text, 'html.parser')
                news = soup.find_all('h4', {'class': 'news-card__title'})
                post = [i for i in news if is_article(str(i))]
                count_urls = len(post)
        for article in post[:self.config.get_num_articles()]:
            self.urls.append(self._extract_url(article_bs=article))

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
        self.article = Article(url=self.full_url, article_id=self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        content_body = article_soup.find('section', {'class': 'article-body'})
        paragraphs_body = content_body.find_all('p')
        text_body = ''.join(i.text.strip() for i in paragraphs_body)
        self.article.text = text_body

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find('h1', {'class':'article-head__title'})
        if title:
            self.article.title = title.text
        info = article_soup.find('div', {'class':'article-head__info'})
        authors = info.find_all('a')
        authors_list = []
        for author in authors:
            author_cleared = [str(tag) for tag in author][0].strip()
            authors_list.append(author_cleared)
        self.article.author = authors_list
        self.article.date = self.unify_date_format(date_str=str(info.span.get('date-time')))
        tags_list = []
        tags = article_soup.find_all('div', {'class':'article-footer__hashtags-item'})
        if tags:
            for tag in tags:
                tags_list.append(tag.text.strip())
            self.article.topics = tags_list
        else:
            self.article.topics = ['none']

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%d.%m.%Y %H:%M:%S')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(url=self.full_url, config=self.config)
        soup = BeautifulSoup(response.text, 'html.parser')
        self._fill_article_with_text(article_soup=soup)
        self._fill_article_with_meta_information(article_soup=soup)
        return self.article


def prepare_environment(base_path: Union[Path, str]) -> None:
    """
    Creates ASSETS_PATH folder if no created and removes existing folder
    """
    path_for_environment = Path(base_path)

    if path_for_environment.exists():
        shutil.rmtree(path_for_environment)
    path_for_environment.mkdir(parents=True)


def main() -> None:
    """
    Entrypoint for scrapper module
    """
    config = Config(CRAWLER_CONFIG_PATH)
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
