"""
Implementation of POSFrequencyPipeline for score ten only.
"""
import re
from typing import Optional
from pathlib import Path

from core_utils.article.article import Article, ArtifactType
from lab_6_pipeline.pipeline import ConlluToken, CorpusManager, ConlluSentence, MorphologicalTokenDTO
from core_utils.article.ud import extract_sentences_from_raw_conllu
from core_utils.constants import ASSETS_PATH
from core_utils.article.io import to_meta
from core_utils.visualizer import visualize

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

    conllu_sentences = []

    sentences = extract_sentences_from_raw_conllu(conllu_text)
    for one_sentence in sentences:
        ud_tokens = one_sentence['tokens']
        conllu_tokens = [_parse_conllu_token(token) for token in ud_tokens]
        conllu_sentence = ConlluSentence(position=one_sentence['position'],
                                         text=one_sentence['text'],
                                         tokens=conllu_tokens)
        conllu_sentences.append(conllu_sentence)

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
    token_components = token_line.split('\t')

    position = token_components[0]
    text = token_components[1]
    lemma = token_components[2]
    pos = token_components[3]
    tags = token_components[4:10]

    morphological_parameters = MorphologicalTokenDTO(lemma=lemma, pos=pos, tags=tags)

    conllu_token = ConlluToken(text)
    conllu_token.set_position(position)
    conllu_token.set_morphological_parameters(morphological_parameters)

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
        articles = self._corpus_manager.get_articles()
        for idx, article in articles.items():
            path_article = Path(ASSETS_PATH / article.url)
            if not path_article.stat().st_size:
                raise EmptyFileError

            conllu_path = ASSETS_PATH / article.get_file_path(kind=ArtifactType.MORPHOLOGICAL_CONLLU)
            if not conllu_path.stat().st_size:
                raise EmptyFileError

            frequencies = {}
            article = from_conllu(conllu_path, article)
            frequencies = self._count_frequencies(article)

            article.set_pos_info(frequencies)
            to_meta(article)

            visualize(article=article, path_to_save=ASSETS_PATH / f'{idx}_image.png')


    def _count_frequencies(self, article: Article) -> dict[str, int]:
        """
        Counts POS frequency in Article
        """
        all_pos = []
        frequencies = {}
        conllu_sentences = article.get_conllu_sentences()
        tokens_sequence = [element.get_tokens() for element in conllu_sentences]

        for tokens in tokens_sequence:
            all_pos.extend([token.get_morphological_parameters().pos for token in tokens])


        parts_of_speech = ['NOUN', 'ADJ', 'ADV', 'VERB', 'NUM', 'ADP', 'CCONJ', 'X', 'PUNCT']

        for element in parts_of_speech:
            frequencies[element] = frequencies.get(element, 0) + all_pos.count(element)

        return frequencies




def main() -> None:
    """
    Entrypoint for the module
    """
    corpus_manager = CorpusManager(path_to_raw_txt_data=ASSETS_PATH)
    posfrequency_pipeline = POSFrequencyPipeline(corpus_manager)
    posfrequency_pipeline.run()


if __name__ == "__main__":
    main()
