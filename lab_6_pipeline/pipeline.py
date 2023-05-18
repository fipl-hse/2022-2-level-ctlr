"""
Pipeline for CONLL-U formatting
"""
import re
import pymorphy2
from pathlib import Path
import json
from typing import List
from pymystem3 import Mystem

from core_utils.constants import ASSETS_PATH
from core_utils.article.article import Article
from core_utils.article.io import from_raw, from_meta, to_cleaned, to_conllu
from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter


# pylint: disable=too-few-public-methods

class InconsistentDatasetError(Exception):
    """
    IDs contain slips, number of meta and raw files is not equal, files are empty
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
        self._storage = {}
        self.path = path_to_raw_txt_data
        self._validate_dataset()
        self._scan_dataset()

    def _validate_dataset(self) -> None:
        """
        Validates folder with assets
        """
        if not isinstance(self.path, Path) or not self.path.exists():
            raise FileNotFoundError

        if not self.path.is_dir():
            raise NotADirectoryError

        if not self.path.glob("*"):
            raise EmptyDirectoryError

        if not list(self.path.iterdir()):
            raise EmptyDirectoryError

        meta_list = [elem.name for elem in self.path.glob("*_meta.json")]
        raw_list = [elem.name for elem in self.path.glob("*_raw.txt")]
        meta_ids = []
        raw_ids = []

        for element in meta_list:
            if re.search(r'\S+(?=_meta.json)', element):
                meta_id = re.search(r'\S+(?=_meta.json)', element)[0]
                if not re.search(r'\d+', meta_id):
                    raise InconsistentDatasetError
                meta_ids.append(int(meta_id))

        for element in raw_list:
            if re.search(r'\S+(?=_raw.txt)', element):
                raw_id = re.search(r'\S+(?=_raw.txt)', element)[0]
                if not re.search(r'\d+', raw_id):
                    raise InconsistentDatasetError
                raw_ids.append(int(raw_id))

        right_list = list(range(1, max(sorted(meta_ids)[-1], sorted(raw_ids)[-1])+1))

        for raw, meta in zip(self.path.glob("*_raw.txt"), self.path.glob("*_meta.json")):
            if Path(raw).stat().st_size == 0 or Path(meta).stat().st_size == 0:
                raise InconsistentDatasetError

        if len(meta_list) != len(raw_list):
            raise InconsistentDatasetError

        if (sorted(meta_ids) or sorted(raw_ids)) != right_list:
            raise InconsistentDatasetError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for element in self.path.glob("*_raw.txt"):
            article = from_raw(element)
            self._storage[article.article_id] = article

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

    def set_position(self, position) -> None:
        self.position = position

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

        return '\t'.join([position, text, lemma, pos, xpos,
                          feats, head, deprel, deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return re.sub(r'[^\w\s]*', '', self._text.lower())


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
        return '\n'.join(token.get_conllu_text(include_morphological_tags)
                         for token in self._tokens)

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        Creates string representation of the sentence
        """
        sent_id = f'# sent_id = {self._position}\n'
        text = f'# text = {self._text}\n'
        tokens = f'{self._format_tokens(include_morphological_tags)}\n'


        return f'{sent_id}{text}{tokens}'

    def get_cleaned_sentence(self) -> str:
        """
        Returns the lowercase representation of the sentence
        """
        return ' '.join((conllu_token.get_cleaned()
                         for conllu_token in self._tokens
                         if conllu_token.get_cleaned()))

    def get_tokens(self) -> list[ConlluToken]:
        """
        Returns sentences from ConlluSentence
        """
        return self._tokens


class MystemTagConverter(TagConverter):
    """
    Mystem Tag Converter
    """

    def feature_from_pos(self, pos: str) -> list:
        """
        Returns a list of features, that correspond to this POS
        """
        pos_categories = {
            "NOUN": [self.gender, self.animacy, self.case, self.number],
            "ADJ": [self.case, self.number, self.gender, self.animacy],
            "VERB": [self.tense, self.number, self.gender],
            "NUM": [self.case, self.animacy, self.gender],
            "PRON": [self.number, self.case, self.gender]
        }
        return pos_categories.get(pos, [])

    def convert_morphological_tags(self, tags: str) -> str:  # type: ignore
        """
        Converts the Mystem tags into the UD format
        """
        necessary_tags = tags.split('|')[0]
        tags_list = re.findall(r'\w+', necessary_tags)
        pos = self.convert_pos(tags_list[0])
        answer = [pos]
        categories = self.feature_from_pos(pos)
        if not categories:
            return '_'

        for feature in categories:
            ud_tag = [self._tag_mapping[feature][tag]
                      for tag in tags_list
                      if tag in self._tag_mapping[feature]]
            answer.append(f'{feature}={str(ud_tag)}')

        return '|'.join(answer)



    def convert_pos(self, tags: str) -> str:  # type: ignore
        """
        Extracts and converts the POS from the Mystem tags into the UD format
        """
        pos = re.search(r'\w+', tags)[0]
        return self._tag_mapping[self.pos].get(pos)


class OpenCorporaTagConverter(TagConverter):
    """
    OpenCorpora Tag Converter
    """

    def feature_from_pos(self, pos: str):
        """
        Returns a list of features, that correspond to this POS
        """
        pos_categories = {
            "NOUN": [self.animacy, self.case, self.gender, self.number],
            "ADJ": [self.case, self.number, self.gender, self.animacy],
            "VERB": [self.tense, self.number, self.gender],
            "NUM": [self.case, self.animacy, self.gender],
            "PRON": [self.number, self.case, self.gender]
        }
        return pos_categories.get(pos, [])

    def convert_pos(self, tags: OpencorporaTagProtocol) -> str:  # type: ignore
        """
        Extracts and converts POS from the OpenCorpora tags into the UD format
        """
        pos = tags.POS
        return self._tag_mapping[self.pos].get(pos, '')

    def convert_morphological_tags(self, tags: OpencorporaTagProtocol) -> str:  # type: ignore
        """
        Converts the OpenCorpora tags into the UD format
        """
        pos = self.convert_pos(tags)
        answer = []
        categories = self.feature_from_pos(pos)

        if not categories:
            return ''

        for feature in categories:
            tag = getattr(tags, feature.lower(), None)
            if not tag:
                continue
            ud_tag = self._tag_mapping[feature].get(tag, '')
            answer.append(f'{feature}={ud_tag}')

        return '|'.join(answer)


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
        self._morphological_token_dto = MorphologicalTokenDTO()
        self._converter_path = Path(__file__).parent / 'data' / 'mystem_tags_mapping.json'
        self._mystem_tag_converter = MystemTagConverter(self._converter_path)

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        result_list = []
        sentence_list = split_by_sentence(text)
        # maybe we should stem the whole text to make it faster

        for sentence_position, element in enumerate(sentence_list):
            conllu_tokens = []
            mystemmed_sentence = [i for i in self._mystem.analyze(element)
                                  if re.fullmatch(r'[A-Za-zА-Яа-я0-9.]+', i['text'])]

            for token_position, one_word in enumerate(mystemmed_sentence, start=1):

                conllu_token = ConlluToken(one_word['text'])
                conllu_token.set_position(token_position)

                # if not one_word['text'].isspace():
                if 'analysis' in one_word and one_word['analysis']:
                    about_part = one_word['analysis'][0]['gr']
                    part = re.search(r'\w+', about_part)
                    if part:
                        pos = part[0]
                    else:
                        pos = 'X'
                    lemma = one_word['analysis'][0]['lex']
                    tags = one_word['analysis'][0]['gr']
                    morphological_tags = self._mystem_tag_converter.convert_morphological_tags(tags)
                    pos_ud = self._mystem_tag_converter.convert_pos(pos)

                else:
                    if one_word['text'].isdigit():
                        pos_ud = 'NUM'
                    elif one_word['text'] == '.':
                        pos_ud = 'PUNCT'
                    elif re.search(r'[A-Za-z]+', one_word['text']):
                        pos_ud = 'X'
                    morphological_tags = '_'
                    lemma = one_word['text']

                parameters = MorphologicalTokenDTO(lemma=lemma,
                                                   pos=pos_ud,
                                                   tags=morphological_tags)

                conllu_token.set_morphological_parameters(parameters)
                conllu_tokens.append(conllu_token)

            result_list.append(ConlluSentence(position=sentence_position,
                                              text=element,
                                              tokens=conllu_tokens))

        return result_list

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        article_dict = self._corpus.get_articles()

        for one_article in article_dict.values():
            conllu_sentences = self._process(one_article.text)
            one_article.set_conllu_sentences(conllu_sentences)

            to_cleaned(one_article)
            to_conllu(one_article)
            to_conllu(one_article,
                      include_morphological_tags=True,
                      include_pymorphy_tags=False)



class AdvancedMorphologicalAnalysisPipeline(MorphologicalAnalysisPipeline):
    """
    Preprocesses and morphologically annotates sentences into the CONLL-U format
    """

    def __init__(self, corpus_manager: CorpusManager):
        """
        Initializes MorphologicalAnalysisPipeline
        """
        super().__init__(corpus_manager)
        self._backup_analyzer = pymorphy2.MorphAnalyzer()
        self.tag_mapping_path = Path(__file__).parent / 'data' / 'opencorpora_tags_mapping.json'
        self._backup_tag_converter = OpenCorporaTagConverter(self.tag_mapping_path)



    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        result_list = []
        sentence_list = split_by_sentence(text)
        # maybe we should stem the whole text to make it faster

        for sentence_position, element in enumerate(sentence_list):
            conllu_tokens = []
            mystemmed_sentence = [i for i in self._mystem.analyze(element)
                                  if re.fullmatch(r'[A-Za-zА-Яа-я0-9.]+', i['text'])]

            for token_position, one_word in enumerate(mystemmed_sentence, start=1):

                conllu_token = ConlluToken(one_word['text'])
                conllu_token.set_position(token_position)

                if 'analysis' in one_word and one_word['analysis']:
                    about_part = one_word['analysis'][0]['gr']
                    part = re.search(r'\w+', about_part)

                    if not part:
                        continue

                    pos = part[0]
                    if pos == 'S':
                        pymorphy_analysis = self._backup_analyzer.parse(one_word['text'])[0]
                        if pymorphy_analysis.normal_form:
                            lemma = pymorphy_analysis.normal_form
                        else:
                            lemma = one_word['text']

                        tags = pymorphy_analysis.tag
                        morphological_tags = self._backup_tag_converter.convert_morphological_tags(tags)
                        pos_ud = self._backup_tag_converter.convert_pos(tags)

                    else:
                        lemma = one_word['analysis'][0]['lex']
                        tags = one_word['analysis'][0]['gr']
                        morphological_tags = self._mystem_tag_converter.convert_morphological_tags(tags)
                        pos_ud = self._mystem_tag_converter.convert_pos(pos)

                else:
                    if one_word['text'].isdigit():
                        pos_ud = 'NUM'
                    elif one_word['text'] == '.':
                        pos_ud = 'PUNCT'
                    elif re.search(r'[A-Za-z]+', one_word['text']):
                        pos_ud = 'X'
                    morphological_tags = '_'
                    lemma = one_word['text']

                parameters = MorphologicalTokenDTO(lemma=lemma,
                                                   pos=pos_ud,
                                                   tags=morphological_tags)

                conllu_token.set_morphological_parameters(parameters)
                conllu_tokens.append(conllu_token)

            result_list.append(ConlluSentence(position=sentence_position,
                                              text=element,
                                              tokens=conllu_tokens))

        return result_list


    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        articles = self._corpus.get_articles()

        for article in articles.values():
            sentences = self._process(article.text)
            article.set_conllu_sentences(sentences)
            to_conllu(article,
                      include_morphological_tags=True,
                      include_pymorphy_tags=True)


def main() -> None:
    """
    Entrypoint for pipeline module
    """
    corpus_manager = CorpusManager(path_to_raw_txt_data=ASSETS_PATH)
    one_pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    one_pipeline.run()
    morpho_pipeline = AdvancedMorphologicalAnalysisPipeline(corpus_manager)
    morpho_pipeline.run()




if __name__ == "__main__":
    main()
