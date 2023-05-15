"""
Pipeline for CONLL-U formatting
"""

import re
from pathlib import Path
from string import punctuation
from typing import List

from pymystem3 import Mystem

from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned, to_conllu
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

        if not any(self.path_to_raw_txt_data.iterdir()):
            raise EmptyDirectoryError

        raw_files = list(self.path_to_raw_txt_data.glob(r'*_raw.txt'))
        meta_files = list(self.path_to_raw_txt_data.glob(r'*_meta.json'))

        if len(raw_files) != len(meta_files):
            raise InconsistentDatasetError

        for files in raw_files, meta_files:
            list_existing = sorted(int(re.search(r'\d+', file.stem)[0])
                                   if re.search(r'\d+', file.stem)[0] else 0 for file in files)
            list_ideal = list(range(1, len(files) + 1))
            if list_existing != list_ideal:
                raise InconsistentDatasetError

            if not all(file.stat().st_size for file in files):
                raise InconsistentDatasetError

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
        if include_morphological_tags and self._morphological_parameters.tags:
            feats = self._morphological_parameters.tags
        else:
            feats = '_'
        return '\t'.join([position, text, lemma, pos, '_', feats, '0', 'root', '_', '_'])

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
        text = f'# text = {self._text}\n'
        tokens = f'{self._format_tokens(include_morphological_tags)}\n'
        return f'{sent_id}{text}{tokens}'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        return ' '.join(filter(bool, (token.get_cleaned() for token in self._tokens)))

    def get_tokens(self) -> list[ConlluToken]:
        """
        Returns sentences from ConlluSentence
        """
        return self._tokens


class MystemTagConverter(TagConverter):
    """
    Mystem Tag Converter
    """
    def convert_morphological_tags(self, tags: str) -> str:  # type: ignore
        """
        Converts the Mystem tags into the UD format
        """
        pos = self.convert_pos(tags)
        pos_feats = {
            'NOUN': [self.case, self.number, self.gender, self.animacy],
            'VERB': [self.tense, self.number, self.gender],
            'ADJ': [self.case, self.number, self.gender],
            'NUM': [self.case, self.number, self.gender],
            'PRON': [self.case, self.number, self.gender, self.animacy]
        }
        if pos not in pos_feats:
            return ''

        tags_subbed = re.sub(r'\(.+?\)', lambda x: x.group(0).split('|')[0], tags)
        tags_list = re.findall(r'[а-я]+', tags_subbed)
        tags_formatted = {}

        for tag in tags_list:
            for feat in pos_feats[pos]:
                if tag in self._tag_mapping[feat]:
                    tags_formatted[feat] = self._tag_mapping[feat][tag]

        return '|'.join(f'{k}={v}' for k, v in sorted(tags_formatted.items()))

    def convert_pos(self, tags: str) -> str:  # type: ignore
        """
        Extracts and converts the POS from the Mystem tags into the UD format
        """
        pos = re.match(r'\w+', tags)[0]
        return self._tag_mapping[self.pos][pos]


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
        self._mystem = Mystem()
        tag_mapping_path = Path(__file__).parent / 'data' / 'mystem_tags_mapping.json'
        self._tag_converter = MystemTagConverter(tag_mapping_path)

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        conllu_sentences = []
        result = (i for i in self._mystem.analyze(text))

        for idx_sent, sentence in enumerate(split_by_sentence(text)):
            conllu_tokens = []
            tokens = []

            for token in result:
                if token['text'] not in sentence:
                    continue
                sentence_subbed = re.sub(re.escape(token['text']), '', sentence, 1)
                if any(c.isalnum() for c in token['text']):
                    tokens.append(token)
                if not any(c.isalnum() for c in sentence_subbed):
                    break
            tokens.append({'text': '.'})

            for idx_token, token in enumerate(tokens, start=1):
                if 'analysis' in token and token['analysis']:
                    lex = token['analysis'][0]['lex']
                    pos = self._tag_converter.convert_pos(token['analysis'][0]['gr'])
                    tags = self._tag_converter.convert_morphological_tags(
                        token['analysis'][0]['gr'])
                else:
                    lex = token['text']
                    tags = ''
                    if token['text'] in punctuation:
                        pos = 'PUNCT'
                    elif token['text'].isdigit():
                        pos = 'NUM'
                    else:
                        pos = 'X'

                conllu_token = ConlluToken(token['text'])
                morphology = MorphologicalTokenDTO(lex, pos, tags)
                conllu_token.position = idx_token
                conllu_token.set_morphological_parameters(morphology)
                conllu_tokens.append(conllu_token)

            conllu_sentence = ConlluSentence(idx_sent, sentence, conllu_tokens)
            conllu_sentences.append(conllu_sentence)

        return conllu_sentences

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus.get_articles().values():
            sentences = self._process(article.text)
            article.set_conllu_sentences(sentences)
            to_cleaned(article)
            to_conllu(article, include_morphological_tags=False, include_pymorphy_tags=False)
            to_conllu(article, include_morphological_tags=True, include_pymorphy_tags=False)


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