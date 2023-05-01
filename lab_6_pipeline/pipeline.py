"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List
import re
import os
from string import punctuation

from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class EmptyDirectoryError(Exception):
    """
    directory is empty
    """


class InconsistentDatasetError(Exception):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
    """


def empty_file(files):
    for file in files:
        with open(file) as f:
            f.seek(0, os.SEEK_END)
            if not f.tell():
                raise InconsistentDatasetError


# pylint: disable=too-few-public-methods
class CorpusManager:
    """
    Works with articles and stores them
    """

    def __init__(self, path_to_raw_txt_data: Path):
        """
        Initializes CorpusManager
        """
        self._storage = {}
        self.path_to_raw_txt_data = path_to_raw_txt_data
        self._validate_dataset()
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError
        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError
        if not [x for x in self.path_to_raw_txt_data.iterdir()]:
            raise EmptyDirectoryError

        texts = list(self.path_to_raw_txt_data.glob('**/*.txt'))
        texts_raw = [i for i in texts if re.match(r'\d+_raw', i.name)]
        meta = list(self.path_to_raw_txt_data.glob('**/*.json'))
        meta_f = [i for i in meta if re.match(r'\d+_meta', i.name)]

        if len(texts_raw) != len(meta_f):
            raise InconsistentDatasetError

        text_order = sorted(int(re.match(r'\d+', i.name)[0]) for i in texts_raw)
        meta_order = sorted(int(re.match(r'\d+', i.name)[0]) for i in meta_f)

        if text_order != list(range(1, len(texts_raw) + 1)) or meta_order != list(range(1, len(meta_f) + 1)):
            raise InconsistentDatasetError

        empty_file(meta)
        empty_file(texts)

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in (list(self.path_to_raw_txt_data.glob('*.txt'))):
            if nes_file := re.search(r'(\d+)_raw', str(file)):
                self._storage[int(nes_file[1])] = from_raw(file)

    def get_articles(self) -> dict:
        """
        Returns storage params
        """
        return self._storage


class MorphologicalTokenDTO:
    """
    Stores morphological parameters for each token
    """

    def __init__(self, lemma: str = "", pos: str = "", tags: str = ""):
        """
        Initializes MorphologicalTokenDTO
        """


class ConlluToken:
    """
    Representation of the CONLL-U Token
    """

    def __init__(self, text: str):
        """
        Initializes ConlluToken
        """
        self._text = text

    def set_morphological_parameters(self, parameters: MorphologicalTokenDTO) -> None:
        """
        Stores the morphological parameters
        """

    def get_morphological_parameters(self) -> MorphologicalTokenDTO:
        """
        Returns morphological parameters from ConlluToken
        """

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        String representation of the token for conllu files
        """

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return "".join([i for i in self._text if i not in punctuation]).lower()

class ConlluSentence(SentenceProtocol):
    """
    Representation of a sentence in the CONLL-U format
    """

    def __init__(self, position: int, text: str, tokens: list[ConlluToken]):
        """
        Initializes ConlluSentence
        """
        self._position = position
        self._text = text
        self._tokens = tokens

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        return " ".join([i.get_cleaned() for i in self._tokens if i.get_cleaned()])

    def get_tokens(self) -> list[ConlluToken]:
        """
        Returns sentences from ConlluSentence
        """


class MystemTagConverter(TagConverter):
    """
    Mystem Tag Converter
    """

    def convert_morphological_tags(self, tags: str) -> str:  # type: ignore
        """
        Converts the Mystem tags into the UD format
        """

    def convert_pos(self, tags: str) -> str:  # type: ignore
        """
        Extracts and converts the POS from the Mystem tags into the UD format
        """


class OpenCorporaTagConverter(TagConverter):
    """
    OpenCorpora Tag Converter
    """

    def convert_pos(self, tags: OpencorporaTagProtocol) -> str:  # type: ignore
        """
        Extracts and converts POS from the OpenCorpora tags into the UD format
        """

    def convert_morphological_tags(self, tags: OpencorporaTagProtocol) -> str:  # type: ignore
        """
        Converts the OpenCorpora tags into the UD format
        """


class MorphologicalAnalysisPipeline:
    """
    Preprocesses and morphologically annotates sentences into the CONLL-U format
    """

    def __init__(self, corpus_manager: CorpusManager):
        """
        Initializes MorphologicalAnalysisPipeline
        """
        self._corpus = corpus_manager

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        sentences = split_by_sentence(text)
        conllu_sent = []
        for id, sent in enumerate(sentences, start=1):
            conllu_list = [ConlluToken(text) for text in sent.split()]
            conllu_sent.append(ConlluSentence(id, sent, conllu_list))
        return conllu_sent

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus.get_articles().values():
            sentences = self._process(article.text)
            article.set_conllu_sentences(sentences)
            to_cleaned(article)


class AdvancedMorphologicalAnalysisPipeline(MorphologicalAnalysisPipeline):
    """
    Preprocesses and morphologically annotates sentences into the CONLL-U format
    """

    def __init__(self, corpus_manager: CorpusManager):
        """
        Initializes MorphologicalAnalysisPipeline
        """

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """


def main() -> None:
    """
    Entrypoint for pipeline module
    """
    corpus_manager = CorpusManager(ASSETS_PATH)
    morph_pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    morph_pipeline.run()


if __name__ == "__main__":
    main()
