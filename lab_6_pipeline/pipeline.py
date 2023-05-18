"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List
import re

from pymystem3 import Mystem

from core_utils.article.article import SentenceProtocol, get_article_id_from_filepath, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned, to_conllu
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
        self.path_to_data = path_to_raw_txt_data
        self._storage = {}
        self._validate_dataset()
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not self.path_to_data.exists():
            raise FileNotFoundError

        if not self.path_to_data.is_dir():
            raise NotADirectoryError

        if not any(self.path_to_data.iterdir()):
            raise EmptyDirectoryError

        raw_files = [file for file in self.path_to_data.glob('*_raw.txt')]
        meta_files = [file for file in self.path_to_data.glob(r'*_meta.json')]

        if len(meta_files) != len(raw_files):
             raise InconsistentDatasetError

        for file in raw_files:
            if not file.stat().st_size:
                raise InconsistentDatasetError

        for file in meta_files:
            if not file.stat().st_size:
                raise InconsistentDatasetError

        list_of_raw_ids = []
        for file in raw_files:
            list_of_raw_ids.append(int(file.name[:file.name.index('_')]))
        if sorted(list_of_raw_ids) != list(range(1, len(list_of_raw_ids) + 1)):
            raise InconsistentDatasetError

        list_of_meta_ids = []
        for file in meta_files:
            list_of_meta_ids.append(int(file.name[:file.name.index('_')]))
        if sorted(list_of_meta_ids) != list(range(1, len(list_of_meta_ids) + 1)):
            raise InconsistentDatasetError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        raw_files = [i for i in self.path_to_data.glob('*_raw.txt')]
        for file in raw_files:
            article_id = get_article_id_from_filepath(file)
            self._storage[article_id] = from_raw(path=file)

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
        cleaned_text = re.sub(r'[^\w\s]', '', self._text)
        return cleaned_text.lower()


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
        sent_id = f'# sent_id = {self._position}\n'
        text = f'text = {self._text}\n'
        tokens = f'tokens = {self._format_tokens(include_morphological_tags)}'

        return f'{sent_id}{text}{tokens}'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        sentence = ''
        for token in self._tokens:
            cleaned_token = token.get_cleaned()
            if cleaned_token:
                sentence += cleaned_token + ' '
        sentence = sentence.strip()
        return sentence

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
        mapping_path = Path(__file__).parent / 'data' / 'mystem_tags_mapping.json'
        self._converter = MystemTagConverter(mapping_path)

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        conllu_sentences = []
        sentences = split_by_sentence(text)
        for position, sentence in enumerate(sentences):
            mystem_sentence = self._mystem.analyze(sentence)
            conllu_tokens = []
            token_counter = 0
            for token in mystem_sentence:
                if not re.match(r'\w+|[.]', token['text']):
                    continue
                text = re.sub(r'\s', '', token['text'])
                token_counter += 1
                if token['text'].isalpha() and token.get("analysis"):
                    lemma = token['analysis'][0]['lex']
                    morph_tags = token['analysis'][0]['gr']
                    pos = self._converter.convert_pos(morph_tags)
                elif token['text'].isdigit():
                    lemma = token['text']
                    pos = 'NUM'
                elif '.' in token['text']:
                    lemma = token['text'].strip()
                    pos = 'PUNCT'
                else:
                    lemma = token['text']
                    pos = 'X'

                conllu_token = ConlluToken(text)
                conllu_token.set_position(token_counter)
                conllu_token.set_morphological_parameters(MorphologicalTokenDTO(lemma, pos, ''))
                conllu_tokens.append(conllu_token)
            conllu_sentence = ConlluSentence(position, sentence, conllu_tokens)
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
            to_conllu((article, include_morphological_tags=False, include_pymorphy_tags=False))


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
