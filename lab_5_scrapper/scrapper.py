"""
Crawler implementation
"""
import datetime
import json
import re
import shutil
from pathlib import Path
from random import randint
from time import sleep
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
        config_content = self._extract_config_content()
        self._validate_config_content()
        self._seed_urls = config_content.seed_urls
        self._num_articles = config_content.total_articles
        self._headers = config_content.headers
        self._encoding = config_content.encoding
        self._timeout = config_content.timeout
        self._should_verify_certificate = config_content.should_verify_certificate
        self._headless_mode = config_content.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config, "r", encoding="utf-8") as f:
            config = json.load(f)
        return ConfigDTO(
            config["seed_urls"],
            config["total_articles_to_find_and_parse"],
            config["headers"],
            config["encoding"],
            config["timeout"],
            config["should_verify_certificate"],
            config["headless_mode"],
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
            if not re.match(r"https?://.*/", url) or not isinstance(url, str):
                raise IncorrectSeedURLError

        if not isinstance(config_dto.headers, dict):
            raise IncorrectHeadersError

        if (
            not isinstance(config_dto.total_articles, int)
            or isinstance(config_dto.total_articles, bool)
            or config_dto.total_articles < 1
        ):
            raise IncorrectNumberOfArticlesError

        if config_dto.total_articles > NUM_ARTICLES_UPPER_LIMIT:
            raise NumberOfArticlesOutOfRangeError

        if not isinstance(config_dto.encoding, str):
            raise IncorrectEncodingError

        if (
            not isinstance(config_dto.timeout, int)
            or not TIMEOUT_LOWER_LIMIT < config_dto.timeout < TIMEOUT_UPPER_LIMIT
        ):
            raise IncorrectTimeoutError

        if not isinstance(config_dto.should_verify_certificate, bool) or not isinstance(
            config_dto.headless_mode, bool
        ):
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
    # chooses the amount of time for waiting to make a request
    sleep_time = randint(1, 3)
    sleep(sleep_time)
    request = requests.get(
        url,
        headers=config.get_headers(),
        timeout=config.get_timeout(),
        verify=config.get_verify_certificate(),
    )
    request.encoding = config.get_encoding()
    return request


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
        self._seed_urls = self._config.get_seed_urls()
        self.urls = []

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Finds and retrieves URL from HTML
        """
        href = article_bs.get("href")

        if href and href.startswith("https://irkutskmedia.ru/news/") and 'hashtag' not in href:
            return str(href)  # get a proper link

        return ""

    def find_articles(self) -> None:
        """
        Finds articles
        """
        # iterates over a list of seed
        for seed_url in self._seed_urls:
            res = make_request(seed_url, self._config)
            soup = BeautifulSoup(res.content, "lxml")

            # finds a tag with a link
            for paragraph in soup.find_all('a'):

                # programs stops finding links if it is larger than in the config
                if len(self.urls) >= self._config.get_num_articles():
                    return

                # gets a valid url from a page
                url = self._extract_url(paragraph)

                if not url or url in self.urls:
                    continue

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
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Finds text of article
        """
        # finds tag with text
        main_bs = article_soup.find('div', class_='page-content io-article-body')
        texts_tag = main_bs.find_all("p")
        # stores retrieved text in a list
        final_text = [text.get_text(strip=True) for text in texts_tag]

        # text that should be removed later(text of links beneath article)
        additional_bs = article_soup.find('div', {'id': 'soc_invites_block'}).find_all('strong')
        additional_text = [text.get_text(strip=True) for text in additional_bs]

        for text_to_remove in additional_text:
            if text_to_remove in final_text:
                final_text.remove(text_to_remove)

        self.article.text = "\n".join(final_text)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Finds meta information of article
        """
        title = article_soup.find("h1")

        # checks that found meta-information exists on the site
        if title:
            self.article.title = title.text.strip()

        topic = article_soup.find('a', class_='fn-rubric-a')

        if topic:
            self.article.topics.append(topic.text.strip())

        date = article_soup.find('div', class_='fn-rubric-link')

        if date:
            self.article.date = self.unify_date_format(date.text.strip())
        else:
            date = article_soup.find('p', class_='pldate')
            self.article.date = self.unify_date_format(date.text.strip())

        # the name of authors is not defined on the pages
        self.article.author = ["NOT FOUND"]

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unifies date format
        """
        months = {
            'января': 'January',
            'февраля': 'February',
            'марта': 'March',
            'апреля': 'April',
            'мая': 'May',
            'июня': 'June',
            'июля': 'July',
            'августа': 'August',
            'сентября': 'September',
            'ноября': 'November',
            'осктября': 'October',
            'декабря': 'December'
        }
        # current year, month and date
        this_year = datetime.datetime.today().year
        this_month = datetime.datetime.today().month
        this_date = datetime.datetime.today().day

        # 11:30
        # the pattern is aimed to find date information like in the example above(only time)
        if re.match(r'\d{2}:\d{2}', date_str):
            date = datetime.datetime.strptime(date_str, '%H:%M')
            return date.replace(year=this_year, month=this_month, day=this_date)

        # finds the name of the month in a string
        month_in_date = re.findall(r'[а-я]+', date_str)

        if month_in_date:
            month_in_date = month_in_date[0]

            # translates month's name to English
            eng_date = re.sub(month_in_date, months[month_in_date], date_str)

        # 25 декабря, 11:30
        # the pattern is aimed to find date information like in the example above(without year)
        if re.match(r'(\d{2}) \w+, \1:\1', date_str):
            date_d = datetime.datetime.strptime(eng_date, '%d %B, %H:%M')
            return date_d.replace(year=this_year)

        # 21.04.2023
        # matches when a parsed value has date, month, year in a format above
        # this format is relevant for articles in the top of the page
        if re.match(r'\d{2}.\d{2}.\d{4}', date_str):
            date_d = datetime.datetime.strptime(date_str, '%d.%m.%Y')
            return date_d

        # 25 декабря 2023, 11:30
        # matches when a parsed value has date, month, year and time
        return datetime.datetime.strptime(eng_date, '%d %B %Y, %H:%M')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parses each article
        """
        response = make_request(self.full_url, self.config)
        main_bs = BeautifulSoup(response.text, "lxml")
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

    for identification, url in enumerate(crawler.urls, start=1):
        parser = HTMLParser(
            full_url=url,
            article_id=identification,
            config=configuration
        )
        article = parser.parse()

        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)


if __name__ == "__main__":
    main()
