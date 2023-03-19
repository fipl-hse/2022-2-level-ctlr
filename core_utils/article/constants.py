"""
Constants for Article
"""
import enum


class ArtifactType(enum.Enum):
    """
    Types of artifacts that can be created by text processing pipelines
    """
    CLEANED = 'cleaned'
    MORPHOLOGICAL_CONLLU = 'morphological_conllu'
    FULL_CONLLU = 'full_conllu'
