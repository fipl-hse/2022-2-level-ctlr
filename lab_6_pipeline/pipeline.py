"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List
import re
from string import punctuation
from pymystem3 import Mystem

from core_utils.article.article import SentenceProtocol, split_by_sentence, get_article_id_from_filepath
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class EmptyDirectoryError(Exception):
    """
    directory is empty
    """


class InconsistentDatasetError(Exception):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
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
        if not next(x for x in self.path_to_raw_txt_data.iterdir()):
            raise EmptyDirectoryError

        texts = list(self.path_to_raw_txt_data.glob('**/*.txt'))
        texts_raw = [i for i in texts if re.match(r'\d+_raw', i.name)]
        meta = list(self.path_to_raw_txt_data.glob('**/*.json'))
        meta_f = [i for i in meta if re.match(r'\d+_meta', i.name)]

        text_order = sorted(int(re.match(r'\d+', i.name)[0]) for i in texts_raw)
        meta_order = sorted(int(re.match(r'\d+', i.name)[0]) for i in meta_f)

        if text_order != list(range(1, len(texts_raw) + 1)) or meta_order != list(range(1, len(meta_f) + 1)):
            raise InconsistentDatasetError

        for files in meta_f, texts_raw:
            if not all(i.stat().st_size for i in files):
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
        self._position = 0

    def set_morphological_parameters(self, parameters: MorphologicalTokenDTO) -> None:
        """
        Stores the morphological parameters
        """
        self._morphological_parameters = parameters

    def set_position(self, position: int) -> None:
        """
        Stores the morphological parameters
        """
        self._position = position

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
        punct = punctuation + "№" + "—"
        return "".join([i for i in self._text if i not in punct]).lower()


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
        conllu_tokens = []
        for token in self._tokens:
            conllu_tokens.append(token.get_conllu_text(include_morphological_tags))
        return '\n'.join(conllu_tokens)

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        return f"# sent_id = {self._position}\n# text = {self._text}\n" \
               f"{self._format_tokens(include_morphological_tags)}\n"

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
        self._stemmer = Mystem()
        mapping_path = Path(__file__).parent / 'mystem_tags_mapping.json'
        self._converter = MystemTagConverter(mapping_path)

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        conllu_sentences = []
        for sentence_id, sentence in enumerate(split_by_sentence(text)):
            mystem_sentence = self._stemmer.analyze(sentence)
            conllu_tokens = []
            token_counter = 0
            for token in mystem_sentence:
                if not re.match(r'\w+|[.]', token['text']):
                    continue
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

                conllu_token = ConlluToken(token['text'])
                conllu_token.set_position(token_counter)
                conllu_token.set_morphological_parameters(MorphologicalTokenDTO(lemma, pos, ''))
                conllu_tokens.append(conllu_token)
            conllu_sentence = ConlluSentence(sentence_id, sentence, conllu_tokens)
            conllu_sentences.append(conllu_sentence)
        return conllu_sentences

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus.get_articles().values():
            article.set_conllu_sentences(self._process(article.get_raw_text()))
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
    morph_pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    morph_pipeline.run()


if __name__ == "__main__":
    main()
