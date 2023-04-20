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
    Raises when seed URL does not match standard pattern "https?://w?w?w?.
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Raises when total number of articles is out of range from 1 to 150
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Raises when total number of articles to parse is not integer
    """


class IncorrectHeadersError(Exception):
    """
    Raises when total number of articles to parse is not integer
    """


class IncorrectEncodingError(Exception):
    """
    Raises when encoding does not specified as a string
    """


class IncorrectTimeoutError(Exception):
    """
    Raises when timeout value is not a positive integer less than 60
    """


class IncorrectVerifyError(Exception):
    """
    Raises when verify certificate value does not match bool value either True or False
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
            content = json.load(f)
        return ConfigDTO(**content)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        config_dto = self._extract_config_content()
        if not isinstance(config_dto.seed_urls, list) or not config_dto.seed_urls:
            raise IncorrectSeedURLError

        if not all(re.match('https://?', url) \
                   and isinstance(url, str) for url in config_dto.seed_urls):
            raise IncorrectSeedURLError

        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError

        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError

        if not isinstance(config_dto.total_articles, int) or \
                isinstance(config_dto.total_articles, bool) or \
                config_dto.total_articles < 1:
            raise IncorrectNumberOfArticlesError

        if config_dto.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_dto.timeout, int) or config_dto.timeout \
                not in range(TIMEOUT_LOWER_LIMIT, TIMEOUT_UPPER_LIMIT + 1):
            raise IncorrectTimeoutError

        if not isinstance(config_dto.should_verify_certificate, bool):
            raise IncorrectVerifyError

        if not isinstance(config_dto.headless_mode, bool):
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
        self.config = config
        self.urls = []
        self._seed_urls = config.get_seed_urls()

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        link = article_bs.get('href')
        if isinstance(link, str) and link and link.count('/') == 5 \
                and link.startswith('https://smolnarod.ru/news/'):
            return link
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for seed_url in self._seed_urls:
            response = make_request(seed_url, self.config)
            if response.status_code == 200:
                main_bs = BeautifulSoup(response.text, 'lxml')
                all_links_bs = main_bs.find_all('a')
                for link in all_links_bs:
                    url = self._extract_url(link)
                    if url and url not in self.urls \
                            and (len(self.urls) < self.config.get_num_articles()):
                        self.urls.append(url)

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self._seed_urls


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
        article_body = article_soup.find('div', {'itemprop': 'articleBody'})
        all_paragraphs = article_body.find_all('p')
        strong_par = ''
        if article_body.find('strong'):
            strong_par = article_body.find('strong').text
        elif article_body.find('b'):
            strong_par = article_body.find('b').text
        elif article_body.find('h5'):
            strong_par = article_body.find('h5').text
        paragraph_texts = [par.text.strip() for par in all_paragraphs[1:]]
        paragraph_text = ''.join(paragraph_texts)
        self.article.text = '\n'.join((strong_par, paragraph_text))

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        article_title = article_soup.find('h1', {'class': "entry-title"}).text
        self.article.title = article_title[:(len(article_title)//2)+1]
        author = article_soup.find('span', {'itemprop': "author"})
        if author:
            self.article.author = [auth.text.strip() for auth in author]
        else:
            self.article.author.append('NOT FOUND')
        date = article_soup.find('meta', {'itemprop': "dateModified"}).get('content')
        time = article_soup.find('meta', {'property': "article:published_time"}).get('content')
        if time:
            new_time = str(time)[-14:-6]
            if date and new_time:
                self.article.date = self.unify_date_format(' '.join((str(date), str(new_time))))

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        main_bs = BeautifulSoup(response.text, 'lxml')
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

    for idx, url in enumerate(crawler.urls):
        parser = HTMLParser(full_url=url, article_id=idx + 1, config=configuration)
        text = parser.parse()
        if isinstance(text, Article):
            to_raw(text)
            to_meta(text)


if __name__ == "__main__":
    main()
