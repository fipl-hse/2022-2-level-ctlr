"""
Crawler implementation
"""
import json
import datetime
import re
import shutil
from pathlib import Path
from typing import Pattern, Union
import requests
from bs4 import BeautifulSoup
from core_utils.config_dto import ConfigDTO
from core_utils.constants import (
    CRAWLER_CONFIG_PATH, ASSETS_PATH,
    TIMEOUT_UPPER_LIMIT, TIMEOUT_LOWER_LIMIT
)
from core_utils.article.article import Article
from core_utils.article.io import to_raw, to_meta


class IncorrectSeedURLError(Exception):
    """
      Exception raised when seed_urls value in configuration
      file is not a list of strings or a string is not a valid URL
      """


class NumberOfArticlesOutOfRangeError(Exception):
    """
        Exception raised when total_articles_to_find_and_parse value
        in configuration file is out of range
        """


class IncorrectNumberOfArticlesError(Exception):
    """
     Exception raised when total_articles_to_find_and_parse
     value in configuration file is not an integer greater than 0
     """


class IncorrectHeadersError(Exception):
    """
    Exception raised when headers value in configuration file is not a dictionary
    """


class IncorrectEncodingError(Exception):
    """
    Exception raised when encoding value in configuration file is not a string
    """


class IncorrectTimeoutError(Exception):
    """
    Exception raised when timeout value in configuration file
    is not an integer between 1 and 60
    """


class IncorrectVerifyError(Exception):
    """
    Exception raised when should_verify_certificate
    value in configuration file is not a boolean
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

        with open(self.path_to_config, 'r', encoding='utf-8') as json_file:
            self.content = json.load(json_file)

        self._validate_config_content()

        self._seed_urls = self.content['seed_urls']
        self._num_articles = self.content['total_articles_to_find_and_parse']
        self._headers = self.content['headers']
        self._encoding = self.content['encoding']
        self._timeout = self.content['timeout']
        self._should_verify_certificate = self.content['should_verify_certificate']
        self._headless_mode = self.content['headless_mode']

        self.config_obj = self._extract_config_content()

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        return ConfigDTO(**self.content)

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        if not isinstance(self.content['seed_urls'], list):
            raise IncorrectSeedURLError

        for element in self.content['seed_urls']:
            if not isinstance(element, str):
                raise IncorrectSeedURLError

            if 'https://' not in element:
                raise IncorrectSeedURLError

        if not isinstance(self.content['total_articles_to_find_and_parse'], int)\
                or isinstance(self.content['total_articles_to_find_and_parse'], bool)\
                or self.content['total_articles_to_find_and_parse'] <= 0:
            raise IncorrectNumberOfArticlesError(
                "Total number of articles to parse is not integer"
            )

        if self.content['total_articles_to_find_and_parse'] < 1 \
                or self.content['total_articles_to_find_and_parse'] > 150:
            raise NumberOfArticlesOutOfRangeError(
                "Total number of articles is out of range from 1 to 150"
            )

        if not isinstance(self.content['headers'], dict):
            raise IncorrectHeadersError("Headers are not in a form of dictionary")

        if not isinstance(self.content['encoding'], str):
            raise IncorrectEncodingError(
                "Encoding must be specified as a string"
            )

        if not isinstance(self.content['timeout'], int):
            raise IncorrectTimeoutError

        if self.content['timeout'] <= TIMEOUT_LOWER_LIMIT\
                or self.content['timeout'] > TIMEOUT_UPPER_LIMIT:
            raise IncorrectTimeoutError(
                "Timeout value must be a positive integer less than 60"
            )

        if not isinstance(self.content['headless_mode'], bool):
            raise IncorrectVerifyError

        if not isinstance(self.content['should_verify_certificate'], bool):
            raise IncorrectVerifyError("Verify certificate value must either be True or False")

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
        self.seed_urls = config.get_seed_urls()
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        link = article_bs.get('href')
        if re.fullmatch(r'https://glasnaya.media/\d{4}/\d{2}/\d{2}/\S+/', link):
            return link
        return ''

    def find_articles(self) -> None:
        """
        Finds articles
        """
        for element in self.seed_urls:
            response = make_request(element, self.config)
            if response.status_code != 200:
                continue

            main_bs = BeautifulSoup(response.text, 'lxml')
            paragraphs = main_bs.find_all('h1', {'class': 'elementor-heading-title elementor-size-default'})

            for each_par in paragraphs:
                if len(self.urls) > self.config.get_num_articles():
                    return
                ans = each_par.find_all('a')
                for elem in ans:
                    link = self._extract_url(article_bs=elem)
                    if not link or link in self.urls:
                        continue
                    self.urls.append(link)

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
        self.article = Article(url=full_url, article_id=article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        texts_bs = article_soup.find('div', {
            'class':
                'elementor-section-wrap'})
        texts = texts_bs.find_all('p')
        result = []
        for one_txt in texts:
            result.append(one_txt.get_text(strip=True))
        self.article.text = ' '.join(result)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title_bs = article_soup.find('h1',
                                     {'class':
                                          'elementor-heading-title elementor-size-default'})
        if title_bs:
            self.article.title = title_bs.text

        date_bs = article_soup.find('li', {'itemprop': 'datePublished'})

        if date_bs:
            date_txt = re.search(r'\d{2}/\d{2}/\d{4}', date_bs.text)
            self.article.date = self.unify_date_format(date_txt[0])

        auth_bs = article_soup.find('li', {'itemprop': 'author'})
        auth_txt = re.search(r'\w+\s\w+', auth_bs.text)
        self.article.author = [auth_txt[0]]

        topic_bs = article_soup.find('h3', {'class': 'elementor-heading-title elementor-size-default'})
        topic_txt = topic_bs.find('span').text
        self.article.topics = [topic_txt]

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        return datetime.datetime.strptime(date_str, '%d/%m/%Y')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        article_bs = BeautifulSoup(response.text, 'lxml')
        self._fill_article_with_text(article_bs)
        self._fill_article_with_meta_information(article_bs)
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
    prepare_environment(ASSETS_PATH)
    configuration = Config(path_to_config=CRAWLER_CONFIG_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, full_url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(full_url=full_url, article_id=i, config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
