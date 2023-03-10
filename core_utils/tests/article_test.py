"""
Tests for Article
"""
import datetime
import json
import shutil
import unittest
from pathlib import Path

import pytest

from config.test_params import TEST_PATH
from core_utils.article import article
from core_utils.article.article import Article, ArtifactType, date_from_meta
from core_utils.article.io import from_meta, to_meta, to_raw
from core_utils.tests.utils import universal_setup


class ArticleTest(unittest.TestCase):
    """
    Class for testing Article implementation
    """

    def setUp(self) -> None:
        article.ASSETS_PATH = TEST_PATH
        universal_setup()
        self.article = Article(url='test', article_id=0)

    @pytest.mark.core_utils
    def test_date_from_meta_ideal(self):
        """
        Ideal date_from_meta scenario
        """
        date_time = '2022-11-06 16:30:00'
        expected = datetime.datetime(2022, 11, 6, 16, 30)
        actual = date_from_meta(date_time)
        self.assertEqual(expected, actual)

    @pytest.mark.core_utils
    def test_article_instantiation(self):
        """
        Ensure that Article instance is instantiated correctly
        """
        attrs = ['url', 'title', 'date', 'author', 'topics', 'pos_frequencies']
        error_msg = f"Article instance must possess the following arguments: {', '.join(attrs)}"

        self.assertTrue(all((
            hasattr(self.article, attrs[0]),
            hasattr(self.article, attrs[1]),
            hasattr(self.article, attrs[2]),
            hasattr(self.article, attrs[3]),
            hasattr(self.article, attrs[4]))), error_msg)

    @pytest.mark.core_utils
    def test_article_instances_type(self):
        """
        Ensure that Article constructor is filled with correct instances types
        """
        self.article = from_meta(self.article.get_meta_file_path(), self.article)

        error_msg = 'Check Article constructor: field "url"' \
                    'is supposed to be a string or None'
        self.assertIsInstance(self.article.url, (str, type(None)), error_msg)

        error_msg = 'Check Article constructor: field "title"' \
                    'is supposed to be a string'
        self.assertIsInstance(self.article.title, str, error_msg)

        error_msg = 'Check Article constructor: field "author"' \
                    'is supposed to be a list'
        self.assertIsInstance(self.article.author, list, error_msg)

        error_msg = 'Check Article constructor: field "topics"' \
                    'is supposed to be a list'
        self.assertIsInstance(self.article.topics, list, error_msg)

        error_msg = 'Check Article constructor: field "pos_frequencies"' \
                    'is supposed to be a list'
        self.assertIsInstance(self.article.pos_frequencies, dict, error_msg)

    @pytest.mark.core_utils
    def test_raw_text_file_is_created(self):
        """
        Ensure that a "raw.txt" file is created
        """
        error_msg = "File for article raw text is not created"
        to_raw(self.article)
        self.assertTrue(self.article.get_raw_text_path().is_file(), error_msg)

    @pytest.mark.core_utils
    def test_raw_text_file_is_not_empty(self):
        """
        Ensure that a "raw.txt" file is not empty
        """
        error_msg = "File for article raw text is empty"
        self.assertIsNot(self.article.get_raw_text_path().stat().st_size, 0, error_msg)

    @pytest.mark.core_utils
    def test_meta_file_is_created(self):
        """
        Ensure that a "meta.json" file is created
        """
        error_msg = "File for article meta info is not created"
        to_meta(self.article)
        to_raw(self.article)
        self.assertTrue(self.article.get_meta_file_path().is_file(), error_msg)

    @pytest.mark.core_utils
    def test_meta_file_is_not_empty(self):
        """
        Ensure that a "meta.json" file is not empty
        """
        error_msg = "File for article meta info is empty"
        self.assertIsNot(self.article.get_meta_file_path().stat().st_size, 0, error_msg)

    @pytest.mark.core_utils
    def test_article_get_raw_text_return_str(self):
        """
        Ensure that Article.get_raw_text() method returns a string
        """
        self.assertIsInstance(self.article.get_raw_text(), str)

    # pylint: disable=protected-access
    @pytest.mark.core_utils
    def test_article_get_meta_return_dict(self):
        """
        Ensure that Article.get_meta() method returns article params as a dictionary
        """
        self.article = from_meta(self.article.get_meta_file_path(), self.article)
        self.assertIsInstance(self.article.get_meta(), dict)

    @pytest.mark.core_utils
    def test_article_get_file_path(self):
        """
        Ensure that Article.get_file_path() method gets the correct path
        """
        kind = ArtifactType.MORPHOLOGICAL_CONLLU
        self.assertTrue(isinstance(self.article.get_file_path(kind), Path))

    @pytest.mark.core_utils
    def test_article_get_file_path_raise_error(self):
        """
        Ensure that Article.get_file_path() method raises ValueError
        if kind param is not in accepted kinds
        """
        kind = 'some text'
        with self.assertRaises(AttributeError):
            self.article.get_file_path(kind)

    # pylint: disable=protected-access
    @pytest.mark.core_utils
    def test_article_sets_pos_info(self):
        """
        Ensure that Article adds POS information in metafile
        """
        test_statistics = {'test': 0, 'test1': 1}
        self.article.set_pos_info(test_statistics)

        self.assertEqual({'test': 0, 'test1': 1}, self.article.get_pos_freq())

    @pytest.mark.core_utils
    def test_article_saves_meta_file(self):
        """
        Ensure that Article saves metafile
        """
        self.article = from_meta(self.article.get_meta_file_path(), self.article)
        to_meta(self.article)
        self.assertTrue(self.article.get_meta_file_path().is_file())
        with open(self.article.get_meta_file_path(), encoding='utf-8') as file:
            meta_file = json.load(file)

        self.article = from_meta(self.article.get_meta_file_path(), self.article)
        self.assertEqual(meta_file, self.article.get_meta())

    def tearDown(self) -> None:
        shutil.rmtree(TEST_PATH)
