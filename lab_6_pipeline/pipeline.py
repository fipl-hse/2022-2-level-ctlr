"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List

from core_utils.article.article import Article
import re

from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


# pylint: disable=too-few-public-methods
class InconsistentDatasetError(Exception):
    """
    The dataset is inconsistent,
    such as when the number of raw and meta
    files is not equal, IDs contain slips,
    or files are empty
    """
    pass


class EmptyDirectoryError(Exception):
    """
    The provided directory is empty
    """
    pass


class CorpusManager:
    """
    Works with articles and stores them
    """

    def __init__(self, path_to_raw_txt_data: Path):
        """
        Initializes CorpusManager
        """
        self.path_to_raw_txt_data = path_to_raw_txt_data
        self._validate_dataset()
        self._storage = dict()
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError

        raw_files = [i for i in self.path_to_raw_txt_data.glob(r'*_raw.txt')]
        meta_files = [i for i in self.path_to_raw_txt_data.glob(r'*_meta.json')]
        if len(meta_files) != len(raw_files):
            raise InconsistentDatasetError
        for files in meta_files, raw_files:
            if sorted(int(re.search(r'\d+', i.stem)[0]) for i in files) != list(range(1, len(files) + 1)):
                raise InconsistentDatasetError
            if not all(i.stat().st_size for i in files):
                raise InconsistentDatasetError

        if not any(self.path_to_raw_txt_data.iterdir()):
            raise EmptyDirectoryError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for path in self.path_to_raw_txt_data.glob('*.txt'):
            if not (relevant := re.search(r'(\d+)_raw', path.stem)):
                continue
            self._storage[int(relevant[1])] = from_raw(path)

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
        return re.sub(r'\W+', '', self._text).lower()


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
        return ' '.join(filter(bool, (token.get_cleaned() for token in self._tokens)))

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
        con_sentences = []
        for idx, sentence in enumerate(split_by_sentence(text), 1):
            con_tokens = [ConlluToken(token) for token in sentence.split()]
            con_sentences.append(ConlluSentence(idx, sentence, con_tokens))
        return con_sentences

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
    pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    pipeline.run()


if __name__ == "__main__":
    main()
