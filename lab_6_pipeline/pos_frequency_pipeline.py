"""
Implementation of POSFrequencyPipeline for score ten only.
"""
from typing import Optional
from pathlib import Path

from core_utils.article.article import Article, ArtifactType
from lab_6_pipeline.pipeline import ConlluToken, CorpusManager
from core_utils.article.ud import extract_sentences_from_raw_conllu
from core_utils.constants import ASSETS_PATH

class EmptyFileError(Exception):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
    """

def from_conllu(path: Path, article: Optional[Article] = None) -> Article:
    """
    Populates the Article abstraction with all information from the conllu file
    """
    with open(path, 'r', encoding='utf8') as conllu_file:
        conllu_text = conllu_file.read()

    conllu_sentences = extract_sentences_from_raw_conllu(conllu_text)

    if not article:
        article = Article()
    article.set_conllu_sentences(conllu_sentences)

    return article



def _parse_conllu_token(token_line: str) -> ConlluToken:
    """
    Parses the raw text in the CONLLU format into the CONLL-U token abstraction

    Example:
    '2	произошло	происходить	VERB	_	Gender=Neut|Number=Sing|Tense=Past	0	root	_	_'
    """


# pylint: disable=too-few-public-methods
class POSFrequencyPipeline:
    """
    Counts frequencies of each POS in articles,
    updates meta information and produces graphic report
    """

    def __init__(self, corpus_manager: CorpusManager):
        """
        Initializes PosFrequencyPipeline
        """
        self._corpus_manager = corpus_manager

    def run(self) -> None:
        """
        Visualizes the frequencies of each part of speech
        """
        articles = self._corpus_manager.get_articles()
        for article in articles.values():
            # print(article)
            conllu_path = article.get_file_path(kind=ArtifactType.POS_CONLLU)
            conllu_info = from_conllu(conllu_path, article)
            print(conllu_info.get_conllu_text(True))




    def _count_frequencies(self, article: Article) -> dict[str, int]:
        """
        Counts POS frequency in Article
        """


def main() -> None:
    """
    Entrypoint for the module
    """
    corpus_manager = CorpusManager(path_to_raw_txt_data=ASSETS_PATH)
    posfrequency_pipeline = POSFrequencyPipeline(corpus_manager)
    posfrequency_pipeline.run()


if __name__ == "__main__":
    main()
