from pydantic.dataclasses import dataclass
from typing import List, Optional, Mapping

from atlasclient.data_types import (AtlasNames, AtlasBaseModelObject,
                                    AtlasRelatedCategoryHeader, AtlasRelatedTermHeader,
                                    AtlasRelatedObjectId, AtlasTermCategorizationHeader)


@dataclass
class AtlasGlossaryBaseObject(AtlasNames):
    """
    This is Base Class for Atlas Glossary
    http://atlas.apache.org/api/v2/json_AtlasGlossaryBaseObject.html
    """
    longDescription: Optional[str] = None
    shortDescription: Optional[str] = None
    additionalAttributes: Optional[dict] = None
    classifications: Optional[List] = None


@dataclass
class AtlasGlossaryHeader:
    """
    http://atlas.apache.org/api/v2/json_AtlasGlossaryHeader.html
    """
    displayText: Optional[str] = None
    glossaryGuid: Optional[str] = None
    relationGuid: Optional[str] = None


@dataclass
class AtlasGlossary(AtlasGlossaryBaseObject, AtlasBaseModelObject):
    """
    http://atlas.apache.org/api/v2/json_AtlasGlossary.html
    """
    language: Optional[str] = None
    usage: Optional[str] = None
    terms: Optional[List[AtlasRelatedTermHeader]] = None
    categories: Optional[List[AtlasRelatedCategoryHeader]] = None


@dataclass
class AtlasGlossaryCategory(AtlasGlossaryBaseObject, AtlasBaseModelObject):
    """
    http://atlas.apache.org/api/v2/json_AtlasGlossaryCategory.html
    """
    # Setting a default value to avoid the type error
    anchor: AtlasGlossaryHeader = None
    terms: Optional[AtlasRelatedTermHeader] = None
    childrenCategories: Optional[List[AtlasRelatedCategoryHeader]] = None
    parentCategory: Optional[AtlasRelatedCategoryHeader] = None


@dataclass
class AtlasGlossaryTerm(AtlasGlossaryBaseObject, AtlasBaseModelObject):
    """
    http://atlas.apache.org/api/v2/json_AtlasGlossaryTerm.html
    """
    abbreviation: Optional[str] = None
    anchor: AtlasGlossaryHeader = None
    antonyms: Optional[List[AtlasRelatedTermHeader]] = None
    assignedEntities: Optional[List[AtlasRelatedObjectId]] = None
    categories: Optional[List[AtlasTermCategorizationHeader]] = None
    classifies: Optional[List[AtlasRelatedTermHeader]] = None
    examples: Optional[List[str]] = None
    isA: Optional[List[AtlasRelatedTermHeader]] = None
    preferredTerms: Optional[List[AtlasRelatedTermHeader]] = None
    preferredToTerms: Optional[List[AtlasRelatedTermHeader]] = None
    replacedBy: Optional[List[AtlasRelatedTermHeader]] = None
    replacementTerms: Optional[List[AtlasRelatedTermHeader]] = None
    seeAlso: Optional[List[AtlasRelatedTermHeader]] = None
    synonyms: Optional[List[AtlasRelatedTermHeader]] = None
    translatedTerms: Optional[List[AtlasRelatedTermHeader]] = None
    translationTerms: Optional[List[AtlasRelatedTermHeader]] = None
    usage: Optional[List[str]] = None
    validValues: Optional[List[AtlasRelatedTermHeader]] = None
    validValuesFor: Optional[List[AtlasRelatedTermHeader]] = None


@dataclass
class AtlasGlossaryExtInfo(AtlasGlossary, AtlasGlossaryBaseObject, AtlasBaseModelObject):
    """
    http://atlas.apache.org/api/v2/json_AtlasGlossaryExtInfo.html
    """
    categoryInfo: Optional[Mapping[str, AtlasGlossaryCategory]] = None
    termInfo: Optional[Mapping[str, AtlasGlossaryTerm]] = None
