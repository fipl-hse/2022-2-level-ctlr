"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List
import re
from pymystem3 import Mystem

from core_utils.article.article import SentenceProtocol
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.article.io import from_raw, from_meta, to_cleaned
from core_utils.constants import ASSETS_PATH
from core_utils.article.article import Article, split_by_sentence

class InconsistentDatasetError(Exception):
    """
    Raised when IDs contain slips, number of meta and raw files is not equal, files are empty
    """

class EmptyDirectoryError(Exception):
    """
    Raised when  directory is empty
    """

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

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """

        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError

        texts = list(self.path_to_raw_txt_data.glob('*.txt'))
        meta_info = list(self.path_to_raw_txt_data.glob('*.json'))
        right_texts = sorted([int(re.match(r'\d+', i.name).group()) for i in texts])

        if len(right_texts) != len(meta_info):
            raise InconsistentDatasetError

        num_of_article = 0
        for i in right_texts:
            if i-num_of_article != 1:
                raise InconsistentDatasetError
            with open(i, 'r', encoding= 'utf-8') as f:
                content = f.read()
                if not content:
                    raise EmptyDirectoryError
            num_of_article += 1



    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in (list(self.path_to_raw_txt_data.glob('*.txt'))):
            num = int(re.match(r'\d+', file.name).group())
            if not num:
                continue
            self._storage[num] = from_raw(file)


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
        return re.sub(r'[^\s\w]+', ' ', self._text).lower()


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
        sentence = [token.get_cleaned() for token in self._tokens if token]
        return ' '.join(sentence)

    def get_tokens(self) -> list[ConlluToken]:
        """
        Returns sentences from ConlluSentence
        """
        split_sentence = self._text.split(' ')
        tokenized_sent = []
        for word in split_sentence:
            token = ConlluToken(word)
            tokenized_sent.append(token)
        return tokenized_sent



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
        for id, sentence in enumerate(sentences, start=1):
            conllu_sent.append(ConlluSentence(id, sentence, []))
        return conllu_sent


    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        articles = self._corpus.get_articles().values()
        for article in articles:
            filled_article = from_raw(self._corpus.path_to_raw_txt_data, article)
            sentences = self._process(article.get_raw_text())
            filled_article.set_conllu_sentences(sentences)
            to_cleaned(filled_article)



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


if __name__ == "__main__":
    main()
