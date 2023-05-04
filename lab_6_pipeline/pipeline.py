"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
from typing import List

from core_utils.article.article import Article, SentenceProtocol
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.constants import ASSETS_PATH


class InconsistentDatasetError(BaseException):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(BaseException):
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
        self._scan_dataset()
        self._validate_dataset()
        self._storage = {}
        self.path_to_raw_txt_data = Path(path_to_raw_txt_data)

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not self.path_to_raw_txt_data.exists():
            raise FileNotFoundError

        if not self.path_to_raw_txt_data.is_dir():
            raise NotADirectoryError

        if self.path_to_raw_txt_data.stat().st_size == 0:
            raise EmptyDirectoryError

        meta_files = []
        raw_files = []
        for file in self.path_to_raw_txt_data.iterdir():
            if file.suffix == '.json':
                meta_files.append(file)
            else:
                raw_files.append(file)

        # checks if a number of meta and raw files is equal
        if len(meta_files) != len(raw_files):
            raise InconsistentDatasetError

        for meta, raw in meta_files, raw_files:
            # checks that files are not empty
            if meta.stat().st_size == 0 or raw.stat().st_size == 0:
                raise InconsistentDatasetError

        data_ids = sorted([int(i.name[0]) for i in meta_files], reverse=True)
        # checks that IDs contain no slips
        for idx, id_obj in enumerate(data_ids):
            try:
                if id_obj - data_ids[idx + 1] > 1:
                    raise InconsistentDatasetError

            except IndexError:
                break

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for ind, file in enumerate(sorted(self.path_to_raw_txt_data.glob('*.txt'),
                                          key=lambda path: int(path.stem.rsplit("_", 1)[0])),
                                   start=1):
            article = Article(url=None, article_id=ind)
            article.text = file.read_text(encoding='utf-8')
            self._storage[ind] = article

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


class ConlluToken:
    """
    Representation of the CONLL-U Token
    """

    def __init__(self, text: str):
        """
        Initializes ConlluToken
        """

    def set_morphological_parameters(self, parameters: MorphologicalTokenDTO) -> None:
        """
        Stores the morphological parameters
        """

    def get_morphological_parameters(self) -> MorphologicalTokenDTO:
        """
        Returns morphological parameters from ConlluToken
        """

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        String representation of the token for conllu files
        """

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """


class ConlluSentence(SentenceProtocol):
    """
    Representation of a sentence in the CONLL-U format
    """

    def __init__(self, position: int, text: str, tokens: list[ConlluToken]):
        """
        Initializes ConlluSentence
        """

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """

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

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """


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
    print(corpus_manager._storage)


if __name__ == "__main__":
    main()
