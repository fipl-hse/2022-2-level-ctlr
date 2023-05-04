"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List
import re

from core_utils.article.article import SentenceProtocol, \
    get_article_id_from_filepath, \
    Article, split_by_sentence
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH
from core_utils.article.io import from_raw, to_cleaned

class InconsistentDatasetError(Exception):
    """
    Raised if IDs contain slips, number of meta
    and raw files is not equal, files are empty
    """

class EmptyDirectoryError(Exception):
    """
    Raised if directory is empty
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
        self.json_files = list(self.path_to_raw_txt_data.glob('*_meta.json'))
        self.txt_files = list(self.path_to_raw_txt_data.glob('*_raw.txt'))
        self._validate_dataset()
        self._storage = {}
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError('file does not exist')
        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError('path does not lead to directory')
        if not self.json_files or not self.txt_files:
            raise EmptyDirectoryError('directory is empty')
        len_json, len_txt = len(self.json_files), len(self.txt_files)
        if len_json != len_txt:
            raise InconsistentDatasetError('number of meta and raw files is not equal')
        for json, txt in zip(self.json_files, self.txt_files):
            if not json.stat().st_size or not txt.stat().st_size:
                raise InconsistentDatasetError("files are empty")
        try:
            json_max = max(map(get_article_id_from_filepath, self.json_files))
            txt_max = max(map(get_article_id_from_filepath, self.txt_files))
        except ValueError:
            raise InconsistentDatasetError('files have no IDs in their names')
        if len_json != json_max != txt_max:
            raise InconsistentDatasetError("files' IDs contain slips")

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in self.txt_files:
            idx = get_article_id_from_filepath(file)
            self._storage[idx] = from_raw(file)

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
        return re.sub(r'[^\w\s]', '',  self._text.lower())


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
        sentence_list = [token.get_cleaned() for token in self._tokens
                         if token.get_cleaned()]
        return ' '.join(sentence_list)

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
        conllu_sentences = []
        for idx, sent in enumerate(sentences):
            wordlist = sent.split()
            conllu_wordlist = [ConlluToken(txt) for txt in wordlist]
            conllu_sentences.append(ConlluSentence(idx, sent, conllu_wordlist))
        return conllu_sentences

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        articles = self._corpus.get_articles()
        for id in articles:
            sentences = self._process(articles[id].text)
            articles[id].set_conllu_sentences(sentences)
            to_cleaned(articles[id])


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
    manager = CorpusManager(ASSETS_PATH)
    pipeline = MorphologicalAnalysisPipeline(manager)
    pipeline.run()


if __name__ == "__main__":
    main()
