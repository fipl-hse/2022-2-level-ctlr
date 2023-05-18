"""
Pipeline for CONLL-U formatting
"""
import string
from pathlib import Path
from typing import Generator, List

from pymystem3 import Mystem

from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned, to_conllu
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

        meta_file_paths = list(self.path_to_raw_txt_data.glob('*_meta.json'))
        meta_file_indexes = sorted(int(path.name.split('_')[0]) for path in meta_file_paths)

        if not (len(raw_file_paths) == len(meta_file_paths)):
            raise InconsistentDatasetError(InconsistentDatasetError.__doc__.strip())

        check_for_slips(raw_file_indexes)
        check_for_slips(meta_file_indexes)

        for file in raw_file_paths + meta_file_paths:
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
        postiton = str(self.position)
        text = self._text
        lemma = self._morphological_parameters.lemma
        pos = self._morphological_parameters.pos
        xpos = '_'
        feats = '_'
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join([postiton, text, lemma, pos, xpos, feats, head, deprel, deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        text = self._text
        for i in string.punctuation + '№':
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

    def _format_tokens(self, include_morphological_tags: bool) -> str:
        """
        Formats tokens per newline
        """
        return '\n'.join(token.get_conllu_text(include_morphological_tags) for token in self._tokens)

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        position = f'# sent_id = {self._position}\n'
        text = f'# text = {self._text}\n'
        tokens = f'{self._format_tokens(include_morphological_tags)}\n'

        return position + text + tokens

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
        pos = self.convert_pos(tags)

        pos_categories = {
            'NOUN': [self.gender, self.animacy, self.case, self.number],
            'ADJ': [self.gender, self.animacy, self.case, self.number],
            'VERB': [self.tense, self.number, self.gender],
            'NUM': [self.gender, self.case, self.animacy],
            'PRON': [self.number, self.case]
        }

    def convert_pos(self, tags: str) -> str:  # type: ignore
        """
        Extracts and converts the POS from the Mystem tags into the UD format
        """
        pos = tags.split('=')[0]
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
        self._mystem_analyzer = Mystem()

    def _make_conllu_token(self, token_id: int, token_text: str,
                           lemma: str, pos: str, tags: str) -> ConlluToken:
        token = ConlluToken(token_text)
        token.position = token_id
        morph_params = MorphologicalTokenDTO(lemma, pos, tags)
        token.set_morphological_parameters(morph_params)
        return token

    def _get_tokens(self, result: Generator, sentence: str) -> List:
        """
        Processes sentence to extract tokens in Mystem analyzed format
        """
        tokens = []
        while sentence:
            token = next(result)

            if token['text'] not in sentence:
                continue

            sentence = sentence.replace(token['text'], '', 1)

            if token['text'].isalnum():
                tokens.append(token)

            tokens.append({'text': '.'})
        return tokens

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        conllu_sentences = []

        for sent_position, sent in enumerate(split_by_sentence(text), start=1):
            result = (i for i in self._mystem_analyzer.analyze(sent))
            tokens = self._get_tokens(result, sent)

            conllu_tokens = []
            for token_position, token in enumerate(tokens, start=1):
                token_text = token['text']
                if token['analysis']:
                    lemma = token['analysis'][0]['lex']
                    pos = ''
                    tags = ''
                else:
                    tags = ''
                    lemma = text
                    if text in string.punctuation:
                        pos = 'PUNCT'
                    elif text.isdigit():
                        pos = 'NUM'
                    else:
                        pos = 'X'

                conllu_token = self._make_conllu_token(token_position, token_text, lemma, pos, tags)
                conllu_tokens.append(conllu_token)

            conllu_sentences.append(ConlluSentence(sent_position, sent, conllu_tokens))
        return conllu_sentences

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
