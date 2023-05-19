"""
Pipeline for CONLL-U formatting
"""
import re
from pathlib import Path
from typing import List

from core_utils.article.article import SentenceProtocol, Article, split_by_sentence, get_article_id_from_filepath
from core_utils.article.io import to_cleaned, from_raw
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class InconsistentDatasetError(Exception):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(Exception):
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
        self._meta_files = list(self.path_to_raw_txt_data.glob('*_meta.json'))
        self._raw_files = list(self.path_to_raw_txt_data.glob('*_raw.txt'))
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

        if not self._meta_files and not self._raw_files:
            raise EmptyDirectoryError('directory is empty')

        for raw, meta in zip(self._raw_files, self._meta_files):
            # checks that raw files are not empty
            if raw.stat().st_size == 0 or meta.stat().st_size == 0:
                raise InconsistentDatasetError('files are empty')

        data_ids = [get_article_id_from_filepath(i) for i in self._raw_files]
        max_number = max(data_ids)
        list_of_proper_ids = [ind for ind in range(1, max_number + 1)]

        if sorted(data_ids) != sorted(list_of_proper_ids):
            raise InconsistentDatasetError('files contain slip in ID')

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
        self.lemma = lemma
        self.pos = pos
        self.tags = tags


class ConlluToken:
    """
    Representation of the CONLL-U Token
    """

    def __init__(self, text: str):
        """
        Initializes ConlluToken
        """
        self._text = text
        self._morphological_parameters = MorphologicalTokenDTO()
        self.position = 0

    def set_morphological_parameters(self, parameters: MorphologicalTokenDTO) -> None:
        """
        Stores the morphological parameters
        """
        self._morphological_parameters = parameters

    def get_morphological_parameters(self) -> MorphologicalTokenDTO:
        """
        Returns morphological parameters from ConlluToken
        """
        return self._morphological_parameters

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        String representation of the token for conllu files
        """
        position = str(self.position)
        text = self._text
        lemma = self._morphological_parameters.lemma
        pos = self._morphological_parameters.pos
        x_pos = '_'
        feats = self._morphological_parameters.tags \
            if include_morphological_tags and self._morphological_parameters.tags else '_'
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join([
            position,
            text,
            lemma,
            pos,
            x_pos,
            feats,
            head,
            deprel,
            deps,
            misc
        ])

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

    def _format_tokens(self, include_morphological_tags: bool) -> str:
        return ' '.join(token.get_conllu_text(include_morphological_tags) for token in self._tokens)

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        return f'# sent_id = {self._position}\n' \
               f'# text = {self._text}\n' \
               f'{self._format_tokens(include_morphological_tags)}\n'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        new_sent = [token.get_cleaned() for token in self._tokens if token.get_cleaned()]
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


if __name__ == "__main__":
    main()
