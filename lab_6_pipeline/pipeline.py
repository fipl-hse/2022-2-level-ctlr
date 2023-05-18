"""
Pipeline for CONLL-U formatting
"""
import string

from pymystem3 import Mystem
import re
from pathlib import Path
from typing import List

from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class EmptyDirectoryError(Exception):
    """
    Thrown when the found directory is empty
    """


class InconsistentDatasetError(Exception):
    """
    Thrown when file IDs contain slips; number of raw and meta files is not equal; files are empty
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
            raise FileNotFoundError('Dataset is not found')

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError('Dataset is not a directory')

        if not [file for file in self.path_to_raw_txt_data.iterdir()]:
            raise EmptyDirectoryError('Dataset directory is empty')

        raw_files = [file for file in self.path_to_raw_txt_data.glob(r'*_raw.txt')]
        meta_files = [file for file in self.path_to_raw_txt_data.glob(r'*_meta.json')]

        for file in raw_files:
            if not file.stat().st_size:
                raise InconsistentDatasetError('A dataset file is empty')

        if len(raw_files) != len(meta_files):
            raise InconsistentDatasetError('Number of raw and meta files is not equal')

        if sorted([int(re.match(r'\d+', file.name)[0]) for file in raw_files]) != list(range(1, len(raw_files) + 1)):
            # regex matches number in file name
            raise InconsistentDatasetError('File IDs contain slips')

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in self.path_to_raw_txt_data.glob(r'*_raw.txt'):
            article = from_raw(file)
            self._storage.update({article.article_id: article})

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
        self._position = 0

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
        position = str(self._position)
        text = self._text
        lemma = self._morphological_parameters.lemma
        pos = self._morphological_parameters.pos
        xpos = '_'
        feats = '_'
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join([position, text, lemma, pos, xpos, feats, head, deprel, deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return re.sub(r'[^\w\s]', '', self._text).lower()
        # regex matches everything that's not a word or whitespace


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
        return '\n'.join([token.get_conllu_text(include_morphological_tags) for token in self._tokens])

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
        cleaned_sentence = []
        for token in self._tokens:
            if token.get_cleaned():
                cleaned_sentence.append(token.get_cleaned())
        return ' '.join(cleaned_sentence)

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
        pos = re.search(r'\w+', tags)[0]
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
        self._corpus_manager = corpus_manager
        self._mystem = Mystem()
        self._mapping_path = Path(__file__).parent/'data'/'mystem_tags_mapping.json'
        self._converter = MystemTagConverter(self._mapping_path)

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        punctuation = string.punctuation
        conllu_text = []

        for sent_id, sentence in enumerate(split_by_sentence(text)):
            conllu_processed = []
            result = [token for token in self._mystem.analyze(text)]

            token_id = 0
            for token in result:
                if 'analysis' in token and token['analysis']:
                    lemma = token['analysis'][0]['lex']
                    pos = self._converter.convert_pos(token['analysis'][0]['gr'])
                    morph_param = MorphologicalTokenDTO(lemma, pos)
                else:
                    if token['text'].isdigit():
                        pos = 'NUM'
                    elif token['text'] in punctuation:
                        pos = 'PUNCT'
                    else:
                        continue
                    morph_param = MorphologicalTokenDTO(pos)

                conllu_token = ConlluToken(token['text'].strip())
                conllu_token._position = token_id
                token_id += 1
                conllu_token.set_morphological_parameters(morph_param)
                conllu_processed.append(conllu_token)

            conllu_text.append(ConlluSentence(sent_id, sentence, conllu_processed))

            return conllu_text

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus_manager.get_articles().values():
            sentences = self._process(article.text)
            article.set_conllu_sentences(sentences)
            to_cleaned(article)
            to_conllu(article)


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
