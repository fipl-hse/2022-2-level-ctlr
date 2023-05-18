"""
Pipeline for CONLL-U formatting
"""
import string
from pathlib import Path
from typing import List

from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class InconsistentDatasetError(Exception):
    """
    Dataset contains slips in IDs of raw files or files are empty
    """


class EmptyDirectoryError(Exception):
    """
    Directory is empty
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
        self.path_to_raw_txt_data = path_to_raw_txt_data
        self._storage = {}

        self._validate_dataset()
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        def check_for_slips(files_list: list) -> None:
            """
            Checks that files' IDs do not have slips
            """
            for i, file_i in enumerate(files_list, start=1):
                if not (i == file_i):
                    raise InconsistentDatasetError(InconsistentDatasetError.__doc__.strip())

        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError('File does not exist')

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError('Path does not lead to directory')

        if not list(self.path_to_raw_txt_data.glob("*")):
            raise EmptyDirectoryError(EmptyDirectoryError.__doc__.strip())

        raw_file_paths = list(self.path_to_raw_txt_data.glob('*_raw.txt'))
        raw_file_indexes = sorted(int(path.name.split('_')[0]) for path in raw_file_paths)

        check_for_slips(raw_file_indexes)

        for file in raw_file_paths:
            if file.stat().st_size == 0:
                raise InconsistentDatasetError(InconsistentDatasetError.__doc__.strip())

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in self.path_to_raw_txt_data.glob('*_raw.txt'):
            ind = int(file.name.split('_')[0])
            self._storage[ind] = from_raw(file)

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
        text = self._text
        for i in string.punctuation + '«»–—…•№€₽£¥¢©™°„“”':
            text = text.replace(i, '')
        return text.lower().strip()


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
        return ' '.join(token.get_cleaned() for token in self._tokens
                        if token.get_cleaned()).strip()

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
        tokenized_sentences = []
        for i, sent in enumerate(sentences, start=1):
            tokens = list(ConlluToken(t) for t in sent.split())
            tokenized_sentences.append(ConlluSentence(i, sent, tokens))
        return tokenized_sentences

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus.get_articles().values():
            article.set_conllu_sentences(self._process(article.text))
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
    corpus_manager = CorpusManager(path_to_raw_txt_data=ASSETS_PATH)
    pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    pipeline.run()


if __name__ == "__main__":
    main()
