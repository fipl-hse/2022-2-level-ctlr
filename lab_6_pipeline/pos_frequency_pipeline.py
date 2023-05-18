"""
Implementation of POSFrequencyPipeline for score ten only.
"""
from typing import Optional
from pathlib import Path
from core_utils.article.article import Article, ArtifactType, get_article_id_from_filepath
from lab_6_pipeline.pipeline import CorpusManager, ConlluSentence, ConlluToken, MorphologicalTokenDTO
from core_utils.article.ud import extract_sentences_from_raw_conllu
from core_utils.visualizer import visualize
from core_utils.constants import ASSETS_PATH
from core_utils.article.io import from_meta, to_meta
from collections import Counter

class EmptyFileError(Exception):
    """
    Exception raised when an article file is empty
    """

def from_conllu(path: Path, article: Optional[Article] = None) -> Article:
    """
    Populates the Article abstraction with all information from the conllu file
    """
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    sentences = extract_sentences_from_raw_conllu(content)
    conllu_sentences = []
    for sentence in sentences:
        parsed_tokens = [_parse_conllu_token(token) for token in sentence['tokens']]
        conllu_sentence = ConlluSentence(position=sentence['position'], text=sentence['text'], tokens=parsed_tokens)
        conllu_sentences.append(conllu_sentence)

    if not article:
        article = Article(None, get_article_id_from_filepath(path))

    article.set_conllu_sentences(conllu_sentences)
    return article


def _parse_conllu_token(token_line: str) -> ConlluToken:
    """
    Parses the raw text in the CONLLU format into the CONLL-U token abstraction

    Example:
    '2	произошло	происходить	VERB	_	Gender=Neut|Number=Sing|Tense=Past	0	root	_	_'
    """
    token_params = token_line.split('\t')
    conllu_token = ConlluToken(token_params[1])
    conllu_token.set_position(int(token_params[0]))
    params = MorphologicalTokenDTO(lemma=token_params[2], pos=token_params[3], tags=token_params[5])
    conllu_token.set_morphological_parameters(params)
    return conllu_token



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
        self.corpus_manager = corpus_manager
    def run(self) -> None:
        """
        Visualizes the frequencies of each part of speech
        """

        articles = self.corpus_manager.get_articles().values()
        for article in articles:
            conllu_path = article.get_file_path(ArtifactType.MORPHOLOGICAL_CONLLU)
            if not conllu_path.stat().st_size:
                raise EmptyFileError

            article = from_conllu(conllu_path, article)
            article = from_meta(article.get_meta_file_path(), article)
            pos = self._count_frequencies(article)
            article.set_pos_info(pos)

            to_meta(article)

            visualize(article, ASSETS_PATH/ f'{article.article_id}_image.png')

    def _count_frequencies(self, article: Article) -> dict[str, int]:
        """
        Counts POS frequency in Article
        """
        pos_count = []
        for sentence in article.get_conllu_sentences():
            for token in sentence.get_tokens():
                pos = token.get_morphological_parameters().pos
                pos_count.append(pos)
        return Counter(pos_count)

def main() -> None:
    """
    Entrypoint for the module
    """
    corpus_manager = CorpusManager(ASSETS_PATH)
    pipeline = POSFrequencyPipeline(corpus_manager)
    pipeline.run()

if __name__ == "__main__":
    main()
