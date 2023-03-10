"""
Article implementation
"""
import enum
from datetime import datetime
from pathlib import Path
from typing import Optional

from core_utils.constants import ASSETS_PATH


class ArtifactType(enum.Enum):
    """
    Types of artifacts that can be created by text processing pipelines
    """
    CLEANED = 'cleaned'
    MORPHOLOGICAL_CONLLU = 'morphological_conllu'
    FULL_CONLLU = 'full_conllu'


def date_from_meta(date_txt: str) -> datetime:
    """
    Converts text date to datetime object
    """
    return datetime.strptime(date_txt, "%Y-%m-%d %H:%M:%S")


class Article:
    """
    Article class implementation.
    Stores article raw, meta and conllu data
    """

    date: Optional[datetime]

    def __init__(self, url: Optional[str], article_id: int) -> None:
        self.url = url
        self.article_id = article_id

        self.title = ''
        self.date = None
        self.author = []
        self.topics = []
        self.text = ''
        self.pos_frequencies = {}

    def set_pos_info(self, pos_freq: dict) -> None:
        """
        Adds POS information in meta file
        """
        self.pos_frequencies = pos_freq

    def get_meta(self) -> dict:
        """
        Gets all meta params
        """
        return {
            'id': self.article_id,
            'url': self.url,
            'title': self.title,
            'date': self._date_to_text() or None,
            'author': self.author,
            'topics': self.topics,
            'pos_frequencies': self.pos_frequencies
        }

    def get_raw_text(self) -> str:
        """
        Gets raw text from the article
        """
        return self.text

    def _date_to_text(self) -> str:
        """
        Converts datetime object to text
        """
        return self.date.strftime("%Y-%m-%d %H:%M:%S") if self.date else ''

    def get_raw_text_path(self) -> Path:
        """
        Returns path for requested raw article
        """
        article_txt_name = f"{self.article_id}_raw.txt"
        return ASSETS_PATH / article_txt_name

    def get_meta_file_path(self) -> Path:
        """
        Returns path for requested raw article
        """
        meta_file_name = f"{self.article_id}_meta.json"
        return ASSETS_PATH / meta_file_name

    def get_file_path(self, kind: ArtifactType) -> Path:
        """
        Returns a proper filepath for an Article instance
        kind: variant of a file -- ArtifactType
        """

        conllu = kind in (ArtifactType.FULL_CONLLU, ArtifactType.MORPHOLOGICAL_CONLLU)

        extension = '.conllu' if conllu else '.txt'
        article_name = f"{self.article_id}_{kind.value}{extension}"

        return ASSETS_PATH / article_name

    def get_pos_freq(self) -> dict:
        """
        Returns a pos_frequency parameter
        """
        return self.pos_frequencies
