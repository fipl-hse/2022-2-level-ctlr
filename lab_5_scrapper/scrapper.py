"""
Crawler implementation
"""
from typing import Pattern, Union
import requests
import re
from bs4 import BeautifulSoup
from pathlib import Path
import json
import shutil
from core_utils.constants import CRAWLER_CONFIG_PATH
from core_utils.config_dto import ConfigDTO


class IncorrectURLError(Exception):
    
    """
    Seed URL does not match standard pattern
    """
    
class IncorrectNumberOfArticlesError(Exception):
    
    """ 
    total number of articles to parse is not integer
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
        self.config_content = self._extract_config_content()
        
        pass

    def _extract_config_content(self) -> ConfigDTO:
        """
        Returns config values
        """
        with open(self.path_to_config) as f:
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
        
        pass

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters
        are not corrupt
        """
        with open(self.path_to_config) as f:
            config = json.load(f)
        
        if not config['seed_urls']:
            raise IncorrectURLError
            
        if not any(re.match(r"https?://w?w?w?.", url) for url in config['seed_urls']):
            raise IncorrectURLError
            
        if not isinstance(config['total_articles_to_find_and_parse'], int):
            raise IncorrectNumberOfArticlesError
            
        if config['total_articles_to_find_and_parse'] not in range(1, 151):
            raise NumberOfArticlesOutOfRangeError
            
        if not isinstance(config['headers'], dict):
            raise IncorrectHeadersError
            
        if not isinstance(config['encoding'], str):
            raise IncorrectEncodingError
            
        if not isinstance(config['timeout'], int):
            raise IncorrectTimeoutError
            
        if config['timeout'] not in range(1, 61):
            raise IncorrectTimeoutError
            
        if not isinstance(config['should_verify_certificate'], bool):
            raise IncorrectVerifyError       
        
        pass

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls
        """
        return self.config_content.seed_urls
        
        pass

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape
        """
        return self.config_content.total_articles_to_find_and_parse
        
        pass

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting
        """
        return self.config_content.headers
        
        pass

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing
        """
        return self.config_content.encoding
        
        pass

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response
        """
        return self.config_content.timeout
        
        pass

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate
        """
        return self.config_content.should_verify_certificate
        
        pass

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode
        """
        return self.config_content.headless_mode
        
        pass


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Delivers a response from a request
    with given configuration
    """
    return requests.get(url, headers=config.get_headers(), timeout=config.get_timeout(), verify=config.get_verify_certificate())

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
        self.conf = config
        self.urls = []
        
        pass

    def _extract_url(self, article_bs: BeautifulSoup) -> list:
        """
        Finds and retrieves URL from HTML
        """
        urls_list = []
        soup_text = article_bs.find_all('h4', {'class': 'news-card__title'})
        for tag in soup_text:
            urls_list.append('https://econs.online/' + tag.a.get('href'))
        
        return urls_list
        pass

    def find_articles(self) -> None:
        """
        Finds articles
        """
        count_urls = 0
        while count_urls < self.conf.get_num_articles():
            for url in self.conf.get_seed_urls():
                response = make_request(url=url, config=self.conf)
                soup = BeautifulSoup(response.text, 'html.parser')
                post = soup.find_all('h4', {'class': 'news-card__title'})
                count_urls = len(post)
        self.urls = self._extract_url(article_bs=soup)[:self.conf.get_num_articles()]
        
        pass

    def get_search_urls(self) -> list:
        """
        Returns seed_urls param
        """
        return self.urls
        
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
    path_for_environment = Path(base_path)

    if path_for_environment.exists():
        shutil.rmtree(path_for_environment)
    path_for_environment.mkdir(parents=True)
    
    pass


def main() -> None:
    """
    Entrypoint for scrapper module
    """    
    conf = Config(CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    craw = Crawler(config=conf)
    craw.find_articles()
    
    pass


if __name__ == "__main__":
    main()
