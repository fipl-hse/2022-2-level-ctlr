"""
Crawler implementation
"""
import requests
from bs4 import BeautifulSoup
from typing import Pattern, Union


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
        pass

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        pass

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        pass

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        pass

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        pass

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        pass

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        pass

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        pass

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        pass

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        pass


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    pass


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
        all_links = []
        delete = []
        for link_bs in all_links_bs:
            link = link_bs.get('href')
            if link is None:
                print(link_bs)
                continue
            elif '/avt/' in link:
                delete.append(link_bs['href'])
                continue
            elif 'http' in link:
                delete.append(link_bs['href'])
                continue
            elif 'www' in link:
                delete.append(link_bs['href'])
                continue
            all_links.append(link_bs['href'])
        print(all_links)

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
    pass


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
        parser = HTMLParser(full_url=url, article id=idx+1, config=configuration)


if __name__ == "__main__":
    main()
