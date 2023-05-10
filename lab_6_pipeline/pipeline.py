"""
Pipeline for CONLL-U formatting
"""
import os.path
import re
from pathlib import Path
import json
from typing import List
from pymystem3 import Mystem

from core_utils.constants import ASSETS_PATH
from core_utils.article.article import Article
from core_utils.article.io import from_raw, from_meta, to_cleaned, to_conllu
from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter


# pylint: disable=too-few-public-methods

class InconsistentDatasetError(Exception):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(Exception):
    """
    Directory is empty
    """

class CorpusManager:
    """
    Works with articles and stores them
    """

    def __init__(self, path_to_raw_txt_data: Path):
        """
        Initializes CorpusManager
        """
        self._storage = {}
        self.path = path_to_raw_txt_data
        self._validate_dataset()
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not isinstance(self.path, Path) or not self.path.exists():
            raise FileNotFoundError

        if not self.path.is_dir():
            raise NotADirectoryError

        if not self.path.glob("*"):
            raise EmptyDirectoryError

        meta_list = [elem.name for elem in self.path.glob("*_meta.json")]
        raw_list = [elem.name for elem in self.path.glob("*_raw.txt")]

        meta_ids = sorted([int(re.search(r'\d+', elem)[0]) for elem in meta_list])
        raw_ids = sorted([int(re.search(r'\d+', elem)[0]) for elem in raw_list])

        right_list = list(range(1, max(meta_ids[-1], raw_ids[-1])+1))

        for raw, meta in zip(self.path.glob("*_raw.txt"), self.path.glob("*_meta.json")):
            if os.stat(raw).st_size == 0 or os.stat(meta).st_size == 0:
                raise InconsistentDatasetError

        if len(meta_list) != len(raw_list):
            raise InconsistentDatasetError

        if meta_ids != right_list or raw_ids != right_list:
            raise InconsistentDatasetError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for element in self.path.glob("*.txt"):
            article = from_raw(element)
            self._storage[article.article_id] = article

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
        self.position = 0
        self._morphological_parameters = MorphologicalTokenDTO()

    def set_position(self, position) -> None:
        self.position = position

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
        xpos = '_'
        feats = '_'
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'

        return '\t'.join([position, text, lemma, pos, xpos,
                          feats, head, deprel, deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return re.sub(r'[^\w\s]', '', self._text.lower())


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
        """
        Formats tokens per newline
        """
        return '\n'.join(token.get_conllu_text(include_morphological_tags)
                         for token in self._tokens)

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        sent_id = f'# sent_id = {self._position}\n'
        text = f'text = {self._text}\n'
        tokens = f'tokens = {self._format_tokens(include_morphological_tags)}'

        return f'{sent_id}{text}{tokens}'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        cleaned_tokens = [conllu_token.get_cleaned() for conllu_token in self._tokens]
        return ' '.join(cleaned_tokens)

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
        result_list = []
        sentence_list = split_by_sentence(text)

        for position, element in enumerate(sentence_list):
            conllu_tokens = []
            words_in_sentence = element.split()

            for token_position, one_word in enumerate(words_in_sentence):
                conllu_token = ConlluToken(one_word)
                conllu_token.set_position(token_position)
                conllu_tokens.append(conllu_token)

            result_list.append(ConlluSentence(position=position,
                                              text=element,
                                              tokens=conllu_tokens))
        return result_list

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        article_dict = self._corpus.get_articles()

        for one_article in article_dict.values():
            conllu_sentences = self._process(one_article.text)
            one_article.set_conllu_sentences(conllu_sentences)
            to_cleaned(one_article)
            to_conllu(one_article)



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
    morpho_pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    morpho_pipeline.run()


if __name__ == "__main__":
    main()
