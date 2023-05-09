"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from pymystem3 import Mystem
import re
from typing import List
import string

from core_utils.article.article import SentenceProtocol
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.constants import ASSETS_PATH
from core_utils.article.article import Article, split_by_sentence


class InconsistentDatasetError(Exception):
    """
    Raised when IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(Exception):
    """
    Raised when  directory is empty
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
        self._storage = {}
        self.path_to_raw_txt_data = path_to_raw_txt_data
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

        if not list(self.path_to_raw_txt_data.iterdir()):
            raise EmptyDirectoryError

        texts = list(self.path_to_raw_txt_data.glob('*_raw.txt'))
        meta_info = list(self.path_to_raw_txt_data.glob('*_meta.json'))
        right_texts = sorted([int(re.match(r'\d+', i.name).group()) for i in texts])

        if len(right_texts) != len(meta_info):
            raise InconsistentDatasetError

        for i in texts + meta_info:
            if not i.stat().st_size:
                raise InconsistentDatasetError
            if sorted([int(re.match(r'\d+', i.name).group()) for i in texts]) \
                    != list(range(1, len(texts)+1)):
                raise InconsistentDatasetError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in (list(self.path_to_raw_txt_data.glob('*_raw.txt'))):
            num = int(re.match(r'\d+', file.name).group())
            self._storage[num] = from_raw(file)


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
        self._position = 0
        self._morphological_parameters = MorphologicalTokenDTO()

    def set_morphological_parameters(self, parameters: MorphologicalTokenDTO) -> None:
        """
        Stores the morphological parameters
        """
        self. _morphological_parameters = parameters

    def get_morphological_parameters(self) -> MorphologicalTokenDTO:
        """
        Returns morphological parameters from ConlluToken
        """
        return self._morphological_parameters
    def set_position(self, position: int) -> None:
        """
        Stores the position
        """
        self._position = position

    def get_position(self) -> int:
        """
        Return the positions of the token
        """
        return self._position

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        String representation of the token for conllu files
        """
        position = self._position
        text = self._text
        lemma = self._morphological_parameters.lemma
        pos = self._morphological_parameters.pos
        xpos = '_'
        feats = '_'
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join([str(position), text, lemma, pos, xpos, feats, head, deprel, deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return re.sub(r'[^\w\s]*', '', self._text).lower()


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
        return (
            f'# sent_id = {self._position}\n'
            f'# text = {self._text}\n'
            f'{self._format_tokens(include_morphological_tags)}\n'
        )

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
        return '\n'.join(token.get_conllu_text(include_morphological_tags) for token in self._tokens)


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
        return self._tag_mapping[self.pos].get(tags)

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
        self._converter_path = Path(__file__).parent/'data'/'mystem_tags_mapping.json'

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        sentences = split_by_sentence(text)
        conllu_sent = []
        punct = '!"#$%&()*+,-/:;<=>?@[\]^_`{|}~'
        for sent_id, sentence in enumerate(sentences):
            conllu_tokens = []
            result = [i for i in self._mystem.analyze(sentence) if (i['text'].strip()
                                                                    not in punct and i['text'].strip())]
            for token_id, token in enumerate(result, start=1):
                conllu_token = ConlluToken(token['text'])
                conllu_token.set_position(token_id)
                if token.get('analysis'):
                    lemma = token['analysis'][0]['lex']
                    pos = re.match(r'[A-Z]+', token['analysis'][0]['gr']).group()
                    ud_pos = MystemTagConverter(self._converter_path).convert_pos(pos)
                    tags = token['analysis'][0]['gr']
                    parameters = MorphologicalTokenDTO(lemma, ud_pos, tags)
                else:
                    if token['text'].isdigit():
                        pos = 'NUM'
                    elif token['text'] == '.':
                        pos = 'PUNCT'
                    else:
                        pos = 'X'
                    parameters = MorphologicalTokenDTO(token['text'], pos)
                conllu_token.set_morphological_parameters(parameters)
                conllu_tokens.append(conllu_token)
            conllu_sent.append(ConlluSentence(sent_id, sentence, conllu_tokens))
        return conllu_sent


    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        articles = self._corpus.get_articles().values()
        for article in articles:
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

    corpus_manager = CorpusManager(ASSETS_PATH)
    pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    pipeline.run()

if __name__ == "__main__":
    main()

