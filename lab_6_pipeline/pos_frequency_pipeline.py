"""
Implementation of POSFrequencyPipeline for score ten only.
"""
from pathlib import Path
from typing import Optional
import core_utils.article.article as article_instance
import core_utils.constants as const
from core_utils.article.article import Article, get_article_id_from_filepath, ArtifactType
from core_utils.article.io import to_meta, from_meta
from core_utils.article.ud import extract_sentences_from_raw_conllu
from core_utils.visualizer import visualize
from lab_6_pipeline.pipeline import ConlluToken, CorpusManager, MorphologicalTokenDTO, ConlluSentence


class EmptyFileError(Exception):
    """
    Raised when a file is empty
    """


def from_conllu(path: Path, article: Optional[Article] = None) -> Article:
    """
    Populates the Article abstraction with all information from the conllu file
    """
    with open(path, 'r', encoding='utf-8') as infile:
        file = infile.read()
        if not file:
            raise EmptyFileError
    info = extract_sentences_from_raw_conllu(file)
    for sent in info:
        sent['tokens'] = [_parse_conllu_token(token) for token in sent['tokens']]
    sentences = [ConlluSentence(**sent) for sent in info]
    if article is None:
        article_id = get_article_id_from_filepath(path)
        article = Article(url=None, article_id=article_id)
    article.set_conllu_sentences(sentences)
    return article


def _parse_conllu_token(token_line: str) -> ConlluToken:
    """
    Parses the raw text in the CONLLU format into the CONLL-U token abstraction

    Example:
    '2	произошло	происходить	VERB	_	Gender=Neut|Number=Sing|Tense=Past	0	root	_	_'
    """

    position, text, lemma, pos, xpos, feats, *args = token_line.split('\t')
    conllu_token = ConlluToken(text)
    conllu_token.set_morphological_parameters(MorphologicalTokenDTO(lemma, pos, feats if feats != '_' else ''))
    conllu_token.set_position(position)
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
        self._corpus_manager = corpus_manager

    def run(self) -> None:
        """
        Visualizes the frequencies of each part of speech
        """
        for key, value in self._corpus_manager.get_articles().items():
            article = from_conllu(value.get_file_path(ArtifactType.MORPHOLOGICAL_CONLLU))
            article = from_meta(const.ASSETS_PATH / f'{article.article_id}_meta.json', article=article)
            count_frequencies = self._count_frequencies(article)
            article.set_pos_info(count_frequencies)
            to_meta(article)
            print(const.ASSETS_PATH)
            visualize(article=article, path_to_save=article_instance.ASSETS_PATH / f'{article.article_id}_image.png')

    def _count_frequencies(self, article: Article) -> dict[str, int]:
        """
        Counts POS frequency in Article
        """
        dct = {}
        for sent in article.get_conllu_sentences():
            for token in sent.get_tokens():
                token_pos = token.get_morphological_parameters().pos
                if token_pos not in dct:
                    dct[token_pos] = 0
                dct[token_pos] += 1
        return dct


def main() -> None:
    """
    Entrypoint for the module
    """
    corpus_manager = CorpusManager(const.ASSETS_PATH)
    POSFrequencyPipeline(corpus_manager).run()


if __name__ == "__main__":
    main()
