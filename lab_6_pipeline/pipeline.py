"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List
import string



from core_utils.article.article import SentenceProtocol, split_by_sentence, get_article_id_from_filepath
from core_utils.article.io import from_raw, to_cleaned
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


# pylint: disable=too-few-public-methods
class InconsistentDatasetError(Exception):
    """
    Exception raised when the dataset is inconsistent
    """
    pass


class EmptyDirectoryError(Exception):
    """
    Exception raised when the directory is empty
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
        self._storage = {}
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError(f"No such file or directory: {self.path_to_raw_txt_data}")

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError(f"Not a directory: {self.path_to_raw_txt_data}")

        meta_files = list(self.path_to_raw_txt_data.glob('*_meta.json'))
        raw_files = list(self.path_to_raw_txt_data.glob('*_raw.txt'))

        if len(meta_files) != len(raw_files):
            raise InconsistentDatasetError('Number of meta and raw files is not equal')

        raw_ind = sorted([int(file.stem.split("_")[0]) for file in raw_files])
        for id1, id2 in zip(raw_ind, raw_ind[1:]):
            if id2 - id1 > 1:
                raise InconsistentDatasetError('Article IDs are not sequential')

        for raw_file in raw_files:
            if raw_file.stat().st_size == 0:
                raise InconsistentDatasetError

        if not raw_files:
            raise EmptyDirectoryError(f"Directory '{self.path_to_raw_txt_data}' is empty")

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
        self.position = 0
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
        xpos = '_'
        feats = '_'
        head = 0
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join((self.position, self._text, self._morphological_parameters.lemma,
                  self._morphological_parameters.pos, xpos, feats, head, deprel, deps, misc))

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return self._text.lower().translate(str.maketrans('', '', string.punctuation))


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
        conllu_tokens = []
        for token in self._tokens:
            conllu_tokens.append(token.get_conllu_text(include_morphological_tags))
        return f"# sent_id = {self._position}\n# text = {self._text}\n" + '\n'.join(conllu_tokens) + '\n'

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

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        sentences = split_by_sentence(text)
        conllu_sentences = [
            ConlluSentence(id, sentence, [ConlluToken(token_text) for token_text in sentence.split()])
            for id, sentence in enumerate(sentences)
        ]
        return conllu_sentences


    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article in self._corpus.get_articles().values():
            sentences = self._process(article.text)
            article.set_conllu_sentences(sentences)
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
    corpus_manager = CorpusManager(ASSETS_PATH)
    morph_pip = MorphologicalAnalysisPipeline(corpus_manager)
    morph_pip.run()

if __name__ == "__main__":
    main()
