"""
Pipeline for CONLL-U formatting
"""
import re
import string
from pathlib import Path
from typing import List

from pymystem3 import Mystem

from core_utils.article.article import (Article, get_article_id_from_filepath,
                                        SentenceProtocol, split_by_sentence)
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class InconsistentDatasetError(Exception):
    """
    IDs contain slips, number of
    meta and raw files is not equal, files are empty
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
        self._storage = dict()
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
        if not any(self.path_to_raw_txt_data.iterdir()):
            raise EmptyDirectoryError
        meta_files = [i for i in self.path_to_raw_txt_data.glob(r'*_meta.json')]
        text_files = [i for i in self.path_to_raw_txt_data.glob(r'*_raw.txt')]
        if len(meta_files) != len(text_files):
            raise InconsistentDatasetError
        for files in meta_files, text_files:
            if sorted(get_article_id_from_filepath(i) for i in files) != list(range(1, len(files) + 1)):
                raise InconsistentDatasetError
            if not all(i.stat().st_size for i in files):
                raise InconsistentDatasetError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for path in self.path_to_raw_txt_data.glob('*_raw.txt'):
            self._storage[get_article_id_from_filepath(path)] = from_raw(path=path)

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

    def __init__(self, text: str, position: int = 0):
        """
        Initializes ConlluToken
        """
        self._text = text
        self.position = position
        self._morphological_parameters = MorphologicalTokenDTO()

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
        
        return '\t'.join([position, text, lemma, pos, xpos, feats, head, deprel, deps, misc])

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
        return '\n'.join(token.get_conllu_text(include_morphological_tags=include_morphological_tags)
                         for token in self._tokens)

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        sent_id = f'# sent_id = {self._position}\n'
        text = f'# text = {self._text}\n'
        tokens = f'{self._format_tokens(include_morphological_tags=include_morphological_tags)}\n'
        
        return f'{sent_id}{text}{tokens}'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        return ' '.join(filter(None, [token.get_cleaned() for token in self._tokens]))

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
        
        if pos:
            return self._tag_mapping[self.pos][pos]
        else:
            return '_'


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
        analysis = [token for token in self._mystem.analyze(text) if token['text'].isalnum() or '.' in token['text']]
        sentence_list = list()
        for sentence_position, sentence in enumerate(split_by_sentence(text)):
            sentence_tokens = list()
            conllu_tokens = list()
            for token_position, token in enumerate(analysis):
                if token['text'].strip() in sentence:
                    sentence_tokens.append(token)
                else:
                    del analysis[:token_position]
                    break
            token_position = 0
            for token in sentence_tokens:
                if 'analysis' in token and token['analysis']:
                    token_position += 1
                    conllu_token = ConlluToken(text=token['text'], position=token_position)
                    morph_params = MorphologicalTokenDTO(lemma=token['analysis'][0]['lex'],
                                                         pos=self._converter.convert_pos(token['analysis'][0]['gr']))
                    conllu_token.set_morphological_parameters(morph_params)
                    conllu_tokens.append(conllu_token)
                elif 'analysis' in token:
                    token_position += 1
                    conllu_token = ConlluToken(text=token['text'], position=token_position)
                    morph_params = MorphologicalTokenDTO(lemma=token['text'],
                                                         pos='X')
                    conllu_token.set_morphological_parameters(morph_params)
                    conllu_tokens.append(conllu_token)
                elif token['text'].isnumeric():
                    token_position += 1
                    conllu_token = ConlluToken(text=token['text'], position=token_position)
                    morph_params = MorphologicalTokenDTO(lemma=token['text'],
                                                         pos='NUM')
                    conllu_token.set_morphological_parameters(morph_params)
                    conllu_tokens.append(conllu_token)
                elif token['text'].strip() == '.':
                    token_position += 1
                    conllu_token = ConlluToken(text=token['text'].strip(), position=token_position)
                    morph_params = MorphologicalTokenDTO(lemma=token['text'].strip(),
                                                         pos='PUNCT')
                    conllu_token.set_morphological_parameters(morph_params)
                    conllu_tokens.append(conllu_token)
            sentence_list.append(ConlluSentence(position=sentence_position,
                                                text=sentence, tokens=conllu_tokens))

        return sentence_list

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus.get_articles().values():
            article.set_conllu_sentences(sentences=self._process(text=article.get_raw_text()))
            to_cleaned(article)
            to_conllu(article,
                      include_morphological_tags=False,
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
    corpus_manager = CorpusManager(path_to_raw_txt_data=ASSETS_PATH)
    analysis = MorphologicalAnalysisPipeline(corpus_manager=corpus_manager)
    analysis.run()


if __name__ == "__main__":
    main()
