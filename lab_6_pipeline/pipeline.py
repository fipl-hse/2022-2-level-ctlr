"""
Pipeline for CONLL-U formatting
"""
import re
from pathlib import Path
from typing import List

from pymystem3 import Mystem

from core_utils.article.article import SentenceProtocol, get_article_id_from_filepath, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


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
        self.path_to_raw_txt_data = path_to_raw_txt_data
        self._storage = {}
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

        meta_files = [meta for meta in self.path_to_raw_txt_data.glob(r'*_meta.json')]
        raw_files = [raw for raw in self.path_to_raw_txt_data.glob(r'*_raw.txt')]

        if len(meta_files) != len(raw_files):
            raise InconsistentDatasetError

        raw_ids = sorted(get_article_id_from_filepath(raw) for raw in raw_files)
        try:
            ids_order = list(range(1, raw_ids[-1] + 1))
            if ids_order != raw_ids:
                raise InconsistentDatasetError
        except IndexError:
            pass

        for files in meta_files, raw_files:
            if not all(file.stat().st_size for file in files):
                raise InconsistentDatasetError

        if not any(self.path_to_raw_txt_data.iterdir()):
            raise EmptyDirectoryError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in self.path_to_raw_txt_data.glob('*_raw.txt'):
            article_id = get_article_id_from_filepath(file)
            self._storage[article_id] = from_raw(file)

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

    def set_position(self, position: int) -> None:
        """
        Stores token's position
        """
        self.position = position

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        String representation of the token for conllu files
        """
        xpos = '_'
        if not self._morphological_parameters.tags or not include_morphological_tags:
            feats = '_'
        else:
            feats = self._morphological_parameters.tags
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join([str(self.position), self._text, self._morphological_parameters.lemma,
                          self._morphological_parameters.pos, xpos, feats, head, deprel,
                          deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return re.sub(r'\W+', '', self._text).replace('_', '').lower()


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
        return f'# sent_id = {self._position}\n'\
               f'# text = {self._text}\n'\
               f'{self._format_tokens(include_morphological_tags)}\n'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        return ' '.join(token.get_cleaned() for token in self._tokens if token.get_cleaned())

    def get_tokens(self) -> list[ConlluToken]:
        """
        Returns sentences from ConlluSentence
        """
        return self._tokens

    def _format_tokens(self, include_morphological_tags: bool) -> str:
        conllu_tokens = []
        for token in self._tokens:
            conllu_tokens.append(token.get_conllu_text(include_morphological_tags))
        return '\n'.join(conllu_tokens)


class MystemTagConverter(TagConverter):
    """
    Mystem Tag Converter
    """

    def convert_morphological_tags(self, tags: str) -> str:  # type: ignore
        """
        Converts the Mystem tags into the UD format
        """
        token_tags = re.findall(r'[а-я]+', tags)
        ud_tags = {}
        for tag in token_tags:
            for parameter in (self.number, self.case, self.gender, self.animacy, self.tense):
                if tag in self._tag_mapping[parameter] and parameter not in ud_tags:
                    ud_tags[parameter] = self._tag_mapping[parameter][tag]
                    break
        return '|'.join(f'{key}={val}' for key, val in sorted(ud_tags.items()))

    def convert_pos(self, tags: str) -> str:  # type: ignore
        """
        Extracts and converts the POS from the Mystem tags into the UD format
        """
        pos = tags.split('=')
        if ',' in pos[0]:
            pos = pos[0].split(',')
        return self._tag_mapping[self.pos][pos[0]]


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
        self.mystem = Mystem()
        tag_mappings_file = Path(__file__).parent / 'data' / 'mystem_tags_mapping.json'
        self.converter = MystemTagConverter(tag_mappings_file)

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        conllu_sentences = []
        for sentence_id, sentence in enumerate(split_by_sentence(text)):
            mystem_sentence = self.mystem.analyze(sentence)
            conllu_tokens = []
            token_counter = 0
            for token in mystem_sentence:
                if not re.match(r'\w+|[.]', token['text']):
                    continue
                token_counter += 1
                if token['text'].isalpha() and token.get("analysis"):
                    lemma = token['analysis'][0]['lex']
                    morph_tags = token['analysis'][0]['gr']
                    pos = self.converter.convert_pos(morph_tags)
                    tags = self.converter.convert_morphological_tags(morph_tags)
                elif token['text'].isdigit():
                    lemma = token['text']
                    pos = 'NUM'
                    tags = ''
                elif '.' in token['text']:
                    lemma = token['text'].strip()
                    pos = 'PUNCT'
                    tags = ''
                else:
                    lemma = token['text']
                    pos = 'X'
                    tags = ''

                conllu_token = ConlluToken(token['text'])
                conllu_token.set_position(token_counter)
                conllu_token.set_morphological_parameters(MorphologicalTokenDTO(lemma, pos, tags))
                conllu_tokens.append(conllu_token)
            conllu_sentence = ConlluSentence(sentence_id, sentence, conllu_tokens)
            conllu_sentences.append(conllu_sentence)
        return conllu_sentences

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus.get_articles().values():
            article.set_conllu_sentences(self._process(article.text))
            to_cleaned(article)
            to_conllu(article, include_morphological_tags=False,
                      include_pymorphy_tags=False)
            to_conllu(article, include_morphological_tags=True,
                      include_pymorphy_tags=False)


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
    morphological_analysis = MorphologicalAnalysisPipeline(manager)
    morphological_analysis.run()


if __name__ == "__main__":
    main()
