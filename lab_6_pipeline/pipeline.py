"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from string import punctuation
from typing import List
import re

from pymystem3 import Mystem

from core_utils.article.article import SentenceProtocol, split_by_sentence, get_article_id_from_filepath
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class InconsistentDatasetError(Exception):
    """
    Check if IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(Exception):
    """
    Check if directory is empty
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
        self._validate_dataset()
        self._storage = {}
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
        for raw_file in self.path_to_raw_txt_data.glob("*_raw.txt"):
            file_id = get_article_id_from_filepath(raw_file)
            self._storage[file_id] = from_raw(raw_file)

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
        lemma = self._morphological_parameters.lemma
        pos = self._morphological_parameters.pos
        xpos = '_'
        feats = self._morphological_parameters.tags \
            if include_morphological_tags else '_'
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join([position, self._text, lemma, pos,
                          xpos, feats, head, deprel, deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return re.sub(r'[^\w\s]+', '', self._text).lower().strip()


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
        Formats each token in a sentence
        to a token for a conllu file
        """
        return '\n'.join([token.get_conllu_text(include_morphological_tags) for token in self._tokens])

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        sent_id = f'# sent_id = {self._position}'
        text = f'# text = {self._text}'
        tokens = self._format_tokens(include_morphological_tags)
        return '\n'.join([sent_id, text, tokens]) + '\n'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        cleaned_sentence = ' '.join(token.get_cleaned() for token in self._tokens)
        cleaned_sentence = re.sub(r'\s+', ' ', cleaned_sentence).strip()
        return cleaned_sentence

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
        part_of_speech = self.convert_pos(re.findall(r'[A-Z]+', tags)[0])
        gramm_categories = {
            'NOUN': [self.gender, self.animacy, self.case, self.number],
            'ADJ': [self.gender, self.animacy, self.case, self.number],
            'VERB': [self.tense, self.number, self.gender],
            'PRON': [self.number, self.case],
            'NUM': [self.gender, self.case, self.animacy]
        }
        necessary_tags = tags.split('|')[0]
        tags_list = re.findall(r'[а-я]+', necessary_tags)
        ud_tags_list = []
        if part_of_speech not in gramm_categories:
            return '_'
        for category in gramm_categories[part_of_speech]:
            ud_tags = [f'{category}={self._tag_mapping[category][tag]}'
                       for tag in tags_list
                       if tag in self._tag_mapping[category]]
            ud_tags_list.extend(ud_tags)
        return '|'.join(sorted(ud_tags_list)) if ud_tags_list else '_'

    def convert_pos(self, tags: str) -> str:  # type: ignore
        """
        Extracts and converts the POS from the Mystem tags into the UD format
        """
        pos = re.findall(r'\w+', tags)[0]
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

        for sent_idx, sentence in enumerate(split_by_sentence(text)):
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

            conllu_sentence = ConlluSentence(sent_idx, sentence, conllu_tokens)
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
    manager = CorpusManager(ASSETS_PATH)
    morph = MorphologicalAnalysisPipeline(manager)
    morph.run()


if __name__ == "__main__":
    main()
