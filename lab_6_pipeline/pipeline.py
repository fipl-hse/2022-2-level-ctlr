"""
Pipeline for CONLL-U formatting
"""
import re
from pathlib import Path
from typing import List

from pymystem3 import Mystem

from core_utils.article.article import Article, SentenceProtocol, split_by_sentence, get_article_id_from_filepath
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH
from core_utils.article.io import from_raw, to_cleaned


class InconsistentDatasetError(BaseException):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(BaseException):
    """
    directory is empty
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
        self._meta_files = list(self.path_to_raw_txt_data.glob('*_meta.json'))
        self._raw_files = list(self.path_to_raw_txt_data.glob('*_raw.txt'))
        self._scan_dataset()
        self._validate_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError

        if not next(self.path_to_raw_txt_data.iterdir(), None):
            raise NotADirectoryError

        if self.path_to_raw_txt_data.stat().st_size == 0:
            raise EmptyDirectoryError

        # checks if a number of meta and raw files is equal
        if len(self._meta_files) != len(self._raw_files):
            raise InconsistentDatasetError

        for raw in self._raw_files:
            # checks that raw files are not empty
            if raw.stat().st_size == 0:
                raise InconsistentDatasetError

        data_ids = sorted([get_article_id_from_filepath(i) for i in self._meta_files], reverse=True)
        # checks that IDs contain no slips
        for idx, id_obj in enumerate(data_ids):
            try:
                if id_obj - data_ids[idx + 1] > 1:
                    raise InconsistentDatasetError

            except IndexError:
                break

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in self._raw_files:
            ind = get_article_id_from_filepath(file)
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
        return re.sub(r'[^\w\s]', '', self._text).lower()


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
        new_sent = [token.get_cleaned() for token in self._tokens]
        return ' '.join(new_sent)

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
        splitted_text = split_by_sentence(text)
        conllu_sent_lst = []

        for pos, text in enumerate(splitted_text):
            conllu_token_lst = [ConlluToken(token) for token in text.split()]
            conllu_sent_lst.append(ConlluSentence(pos, text, conllu_token_lst))

        return conllu_sent_lst

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        storage = self._corpus.get_articles()

        for article in storage.values():
            process = self._process(article.text)
            article.set_conllu_sentences(process)
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
    morph_pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    morph_pipeline.run()
    print(corpus_manager._storage)


if __name__ == "__main__":
    main()
