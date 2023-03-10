"""
I/O operations for Article
"""
import json
from pathlib import Path
from typing import Optional, Union

from core_utils.article.article import Article, date_from_meta


def to_raw(article: Article) -> None:
    """
    Saves raw text
    """
    with open(article.get_raw_text_path(), 'w', encoding='utf-8') as file:
        file.write(article.text)


def to_meta(article: Article) -> None:
    """
    Saves metafile
    """
    with open(article.get_meta_file_path(), 'w', encoding='utf-8') as meta_file:
        json.dump(article.get_meta(),
                  meta_file,
                  indent=4,
                  ensure_ascii=False,
                  separators=(',', ': '))


def from_meta(path: Union[Path, str], article: Optional[Article] = None) -> Article:
    """
    Loads meta.json file into the Article abstraction
    """
    with open(path, encoding='utf-8') as meta_file:
        meta = json.load(meta_file)

    article = article if article else \
        Article(url=meta.get('url', None), article_id=meta.get('id', 0))

    article.article_id = meta.get('id', 0)
    article.url = meta.get('url', None)
    article.title = meta.get('title', '')
    article.date = date_from_meta(meta.get('date', None))
    article.author = meta.get('author', None)
    article.topics = meta.get('topics', None)
    article.pos_frequencies = meta.get('pos_frequencies', None)

    # intentionally leave it empty
    article.text = ''
    return article
