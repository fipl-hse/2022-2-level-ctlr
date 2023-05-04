"""
Pipeline for CONLL-U formatting
"""
import re
from pathlib import Path
from typing import List


from pymystem3 import Mystem

import core_utils.constants as const
from core_utils.article.article import SentenceProtocol, split_by_sentence, get_article_id_from_filepath
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter


class InconsistentDatasetError(Exception):
    """
    Raised when IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(Exception):
    """
    Raised when a directory is empty
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
            raise FileNotFoundError('There are no such files')

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError('Path does not lead to directory')

        meta_files = list(self.path_to_raw_txt_data.glob("*_meta.json"))
        raw_files = list(self.path_to_raw_txt_data.glob("*_raw.txt"))

        if len(meta_files) != len(raw_files):
            raise InconsistentDatasetError("Number of meta and raw files are not equal")

        if not meta_files or not raw_files:
            raise EmptyDirectoryError("The directory is empty")

        file_ids = [int(file.name.split("_")[0]) for file in raw_files]
        if len(file_ids) != len(set(file_ids)):
            raise InconsistentDatasetError("IDs contain duplicates")

        empty_files = [file for file in raw_files if file.stat().st_size == 0]
        if empty_files:
            raise InconsistentDatasetError(f"Files are empty: {empty_files}")

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

    def __init__(self, text: str, morphological_parameters: MorphologicalTokenDTO, position: int):
        """
        Initializes ConlluToken
        """
        self._text = text
        self._morphological_parameters = morphological_parameters
        self._position = position

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
        if include_morphological_tags:
            feats = self._morphological_parameters.tags if self._morphological_parameters.tags else '_'
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
        res = f'# sent_id = {self._position}\n# text = {self._text}\n'

        for token in self._tokens:
            res += token.get_conllu_text(include_morphological_tags) + '\n'

        return res

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        return self._format_tokens(include_morphological_tags)

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        cleaned_sentence = ' '.join(token.get_cleaned() for token in self._tokens)
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
        extracted_tags = re.findall(r'[а-я]+', tags)
        ud_tags = {}
        for tag in extracted_tags:
            for category in (self.case, self.number, self.gender, self.animacy, self.tense):
                if tag in self._tag_mapping[category]:
                    ud_tags[category] = self._tag_mapping[category][tag]
        return '|'.join(f'{k}={v}' for k, v in sorted(ud_tags.items()))

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
        return self._tag_mapping[self.pos][tags.POS]

    def convert_morphological_tags(self, tags: OpencorporaTagProtocol) -> str:  # type: ignore
        """
        Converts the OpenCorpora tags into the UD format
        """
        ud_tags = {}
        lst = [[self.gender, tags.gender], [self.number, tags.number], [self.animacy, tags.animacy],
               [self.case, tags.case]]

        for elem in lst:
            k, v = elem
            if v is not None:
                ud_tags[k] = self._tag_mapping[k][v]
        return '|'.join(f'{k}={v}' for k, v in ud_tags.items())


class MorphologicalAnalysisPipeline:
    """
    Preprocesses and morphologically annotates sentences into the CONLL-U format
    """

    def __init__(self, corpus_manager: CorpusManager):
        """
        Initializes MorphologicalAnalysisPipeline
        """
        self._corpus_manager = corpus_manager
        self._analyzer = Mystem()
        self._tag_converter = MystemTagConverter(Path(__file__).parent / 'data' / 'mystem_tags_mapping.json')

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        conllu_sentences = []
        result = self._analyzer.analyze(re.sub(r'\W+', ' ', text))
        number_of_word = 0
        for ind, sentence in enumerate(split_by_sentence(text), 1):
            tokens = []
            words = re.findall(r'\w+', sentence)
            for i, word in enumerate(words, 1):
                if not result[number_of_word]['text'].isalnum():
                    number_of_word += 1
                analyzed_content = result[number_of_word]
                original_word = analyzed_content['text']
                if 'analysis' in analyzed_content and analyzed_content['analysis']:
                    lemma = analyzed_content['analysis'][0]['lex']
                    morph_tags = analyzed_content['analysis'][0]['gr']
                    pos = self._tag_converter.convert_pos(morph_tags)
                    tags = self._tag_converter.convert_morphological_tags(morph_tags)
                elif analyzed_content['text'].isdigit():
                    lemma = analyzed_content['text']
                    pos = 'NUM'
                    tags = ''
                else:
                    lemma = analyzed_content['text']
                    pos = 'X'
                    tags = ''
                tokens.append(ConlluToken(original_word, MorphologicalTokenDTO(lemma=lemma, pos=pos, tags=tags), i))
                number_of_word += 1
            tokens.append(ConlluToken('.', MorphologicalTokenDTO('.', 'PUNCT'), len(words) + 1))
            conllu_sentence = ConlluSentence(
                position=ind,
                text=sentence,
                tokens=tokens
            )
            conllu_sentences.append(conllu_sentence)

        return conllu_sentences

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for key, value in self._corpus_manager.get_articles().items():
            article = from_raw(value.get_raw_text_path(), value)
            article.set_conllu_sentences(self._process(article.get_raw_text()))
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
    corpus_manager = CorpusManager(const.ASSETS_PATH)
    MorphologicalAnalysisPipeline(corpus_manager).run()


if __name__ == "__main__":
    main()