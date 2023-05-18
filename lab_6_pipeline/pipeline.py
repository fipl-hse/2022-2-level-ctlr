"""
Pipeline for CONLL-U formatting
"""
from pathlib import Path
import pymorphy2
from pymystem3 import Mystem
import re
import time
from typing import List, Optional

from core_utils.article.article import SentenceProtocol, split_by_sentence
from core_utils.article.ud import OpencorporaTagProtocol, TagConverter
from core_utils.article.io import from_raw, to_cleaned, to_conllu
from core_utils.constants import ASSETS_PATH


class InconsistentDatasetError(Exception):
    """
    Raised when IDs contain slips, number of meta and raw files is not equal, files are empty
    """


class EmptyDirectoryError(Exception):
    """
    Raised when  directory is empty
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

        if not list(self.path_to_raw_txt_data.iterdir()):
            raise EmptyDirectoryError

        texts = list(self.path_to_raw_txt_data.glob('*_raw.txt'))
        meta_info = list(self.path_to_raw_txt_data.glob('*_meta.json'))
        right_texts = sorted([int(re.match(r'\d+', i.name).group()) for i in texts])

        if len(right_texts) != len(meta_info):
            raise InconsistentDatasetError

        for i in texts + meta_info:
            if not i.stat().st_size:
                raise InconsistentDatasetError

        if sorted([int(re.match(r'\d+', i.name).group()) for i in texts]) \
                != list(range(1, len(texts)+1)):
            raise InconsistentDatasetError

    def _scan_dataset(self) -> None:
        """
        Register each dataset entry
        """
        for file in (list(self.path_to_raw_txt_data.glob('*_raw.txt'))):
            num = int(re.match(r'\d+', file.name).group())
            self._storage[num] = from_raw(file)

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
        self._position = 0
        self._morphological_parameters = MorphologicalTokenDTO()

    def set_morphological_parameters(self, parameters: MorphologicalTokenDTO) -> None:
        """
        Stores the morphological parameters
        """
        self. _morphological_parameters = parameters

    def get_morphological_parameters(self) -> MorphologicalTokenDTO:
        """
        Returns morphological parameters from ConlluToken
        """
        return self._morphological_parameters

    def set_position(self, position: int) -> None:
        """
        Stores the position
        """
        self._position = position

    def get_position(self) -> int:
        """
        Return the positions of the token
        """
        return self._position

    def get_conllu_text(self, include_morphological_tags: bool) -> str:
        """
        String representation of the token for conllu files
        """
        position = self._position+1
        text = self._text
        lemma = self._morphological_parameters.lemma
        pos = self._morphological_parameters.pos
        xpos = '_'
        if include_morphological_tags:
            feats = self._morphological_parameters.tags
        else:
            feats = '_'
        head = '0'
        deprel = 'root'
        deps = '_'
        misc = '_'
        return '\t'.join([str(position), text, lemma, pos, xpos, feats, head, deprel, deps, misc])

    def get_cleaned(self) -> str:
        """
        Returns lowercase original form of a token
        """
        return re.sub(r'[^\w\s]*', '', self._text).lower()


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
        return (
            f'# sent_id = {self._position}\n'
            f'# text = {self._text}\n'
            f'{self._format_tokens(include_morphological_tags)}\n'
        )

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

    def _format_tokens(self, include_morphological_tags: bool) -> str:
        return '\n'.join(token.get_conllu_text(include_morphological_tags) for token in self._tokens)


class MystemTagConverter(TagConverter):
    """
    Mystem Tag Converter
    """

    def convert_morphological_tags(self, tags: str) -> str:  # type: ignore
        """
        Converts the Mystem tags into the UD format
        """
        tags_list = re.split(r'\W+', re.match(r'[^|]+|', tags).group())
        ud_tags = []
        pos = self.convert_pos(tags)
        pos_categories = {'NOUN': [self.animacy, self.case, self.gender, self.number],
                          'ADJ': [self.case, self.gender, self.number],
                          'PRON': [self.case, self.gender, self.number],
                          'VERB': [self.gender, self.number, self.tense],
                          'NUM': [self.case, self.gender, self.number]}
        if pos in pos_categories.keys():
            for category in pos_categories[pos]:
                for tag in tags_list[1:]:
                    if tag in self._tag_mapping[category].keys():
                        ud_tags.append(f'{category}={self._tag_mapping[category][tag]}')
            if ud_tags:
                return '|'.join(sorted(ud_tags))
        return '_'

    def convert_pos(self, tags: str) -> str:  # type: ignore
        """
        Extracts and converts the POS from the Mystem tags into the UD format
        """
        pos = re.match(r'[A-Z]+', tags).group()
        return self._tag_mapping[self.pos].get(pos)


class OpenCorporaTagConverter(TagConverter):
    """
    OpenCorpora Tag Converter
    """

    def convert_pos(self, tags: OpencorporaTagProtocol) -> str:  # type: ignore
        """
        Extracts and converts POS from the OpenCorpora tags into the UD format
        """
        pos = re.match(r'[A-Z]+', str(tags)).group()
        if pos in self._tag_mapping[self.pos]:
            return self._tag_mapping[self.pos].get(pos)
        return '_'


    def convert_morphological_tags(self, tags: OpencorporaTagProtocol) -> str:  # type: ignore
        """
        Converts the OpenCorpora tags into the UD format
        """
        tags_list = re.split(r'\W+', str(tags))
        ud_tags = []
        '''
        if len(tags_list) > 1:
            for tag in tags_list[1:]:
                for category in self._tag_mapping.keys():
                    if tag in self._tag_mapping[category].keys():
                        ud_tags.append(f'{category}={self._tag_mapping[category][tag]}')
        '''
        if len(tags_list) > 1:
            for tag in tags_list[1:]:
                ud_tags_one = [f'{category}={self._tag_mapping[category][tag]}'
                               for category in self._tag_mapping.keys()
                               if tag in self._tag_mapping[category].keys()]
                ud_tags.extend(ud_tags_one)
            return '|'.join(sorted(ud_tags))
        else:
            return '_'


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
        self._converter_path = Path(__file__).parent/'data'/'mystem_tags_mapping.json'
        self._converter = MystemTagConverter(self._converter_path)
        self._backup_analyzer = None
        self._backup_tag_converter = None

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        sentences = split_by_sentence(text)
        conllu_sent = []
        for sent_id, sentence in enumerate(sentences):
            start_time = time.time()
            conllu_tokens = []
            result = [
                        i
                        for i in self._mystem.analyze(sentence)
                        if re.fullmatch(r'[A-Za-zА-Яа-я0-9.]+', i['text'].strip())
                        ]
            token_ind = 0
            for token in result:
                if 'analysis' in token and token['analysis']:
                    lemma = token['analysis'][0]['lex']
                    ud_pos = self._converter.convert_pos(token['analysis'][0]['gr'])
                    if self._backup_analyzer and ud_pos == 'NOUN':
                        analysis = self._backup_analyzer.parse(token['text'])[0]
                        ud_tags = self._backup_tag_converter.convert_morphological_tags(analysis.tag)
                        ud_pos = self._backup_tag_converter.convert_pos(analysis.tag)
                    else:
                        tags = token['analysis'][0]['gr']
                        ud_tags = self._converter.convert_morphological_tags(tags)
                    parameters = MorphologicalTokenDTO(lemma=lemma, pos=ud_pos, tags=ud_tags)
                else:
                    if token['text'].isdigit():
                        ud_pos = 'NUM'
                    elif token['text'] == '.':
                        ud_pos = 'PUNCT'
                    elif re.fullmatch(r'[A-Za-z]+', token['text']):
                        ud_pos = 'X'
                    else:
                        continue
                    parameters = MorphologicalTokenDTO(lemma=token['text'].strip(), pos=ud_pos, tags= '_')
                conllu_token = ConlluToken(token['text'].strip())
                conllu_token.set_position(token_ind)
                conllu_token.set_morphological_parameters(parameters)
                conllu_tokens.append(conllu_token)
                token_ind += 1
            conllu_sent.append(ConlluSentence(sent_id, sentence, conllu_tokens))
            end_time = time.time()
            #print(f"\tit takes {end_time - start_time} for one sentence")
        return conllu_sent



    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        for article_id, article in self._corpus.get_articles().items():
            start_time = time.time()
            sentences = self._process(article.text)
            article.set_conllu_sentences(sentences)
            to_cleaned(article)
            to_conllu(article, include_morphological_tags=False, include_pymorphy_tags=False)
            to_conllu(article, include_morphological_tags=True, include_pymorphy_tags=False)
            end_time = time.time()
            #print(f"it takes  {end_time - start_time} for ARTICLE #{article_id}")



class AdvancedMorphologicalAnalysisPipeline(MorphologicalAnalysisPipeline):
    """
    Preprocesses and morphologically annotates sentences into the CONLL-U format
    """

    def __init__(self, corpus_manager: CorpusManager):
        """
        Initializes MorphologicalAnalysisPipeline
        """
        super().__init__(corpus_manager)
        self._corpus = corpus_manager
        self._backup_analyzer = pymorphy2.MorphAnalyzer()
        self._path = Path(__file__).parent/'data'/'opencorpora_tags_mapping.json'
        self._backup_tag_converter = OpenCorporaTagConverter(self._path)

    def _process(self, text: str) -> List[ConlluSentence]:
        """
        Returns the text representation as the list of ConlluSentence
        """
        return super()._process(text)

    def run(self) -> None:
        """
        Performs basic preprocessing and writes processed text to files
        """
        articles = self._corpus.get_articles().values()
        for article in articles:
            sentences = self._process(article.text)
            article.set_conllu_sentences(sentences)
            to_cleaned(article)
            to_conllu(article, include_morphological_tags=False, include_pymorphy_tags=False)
            to_conllu(article, include_morphological_tags=True, include_pymorphy_tags=True)

def main() -> None:
    """
    Entrypoint for pipeline module
    """
    corpus_manager = CorpusManager(ASSETS_PATH)
    pipeline = MorphologicalAnalysisPipeline(corpus_manager)
    pipeline.run()
    adv_pipeline = AdvancedMorphologicalAnalysisPipeline(corpus_manager)
    adv_pipeline.run()


if __name__ == "__main__":
    main()

