"""
Crawler implementation
"""
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
        pass

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


class CrawlerRecursive(Crawler):
    """
    Recursive implementation.
    Gets one URL of the title page and finds requested number of articles recursively.
    """

    def __init__(self, config: Config) -> None:
        """
        Initializes an instance of the CrawlerRecursive class
        """
        pass

    def find_articles(self) -> None:
        """
        Finds number of article urls requested
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


if __name__ == "__main__":
    configuration = Config(CRAWLER_CONFIG_PATH)
    print(f"Need to find {configuration.get_num_articles()} articles")
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(config=configuration)
    crawler.find_articles()
    for i, article_url in enumerate(crawler.urls):
        parser = HTMLParser(article_url, article_id=i + 1, config=configuration)
        article = parser.parse()
        if isinstance(article, Article):
            to_raw(article)
            to_meta(article)
    print("Done")
