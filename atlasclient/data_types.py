from dataclasses import asdict
from typing import Optional, Dict, Any

from pydantic.dataclasses import dataclass


class Status:
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


@dataclass
class AtlasBaseModelObject:
    """
    Base class to hold the GUID for each entity of atlas.
    http://atlas.apache.org/api/v2/json_AtlasBaseModelObject.html
    """
    guid: Optional[str] = None

    def _to_dict(self, data_dict, _ignore_falsy):
        _data = dict()
        for key, value in data_dict.items():
            if isinstance(value, dict):
                _data.update({key: self._to_dict(value, _ignore_falsy)})
            elif not _ignore_falsy or (_ignore_falsy and value):
                _data.update({key: value})
        return _data

    def to_dict(self, data_key: str = None, ignore_falsy: str = False) -> Dict[str, Any]:
        data_dict = asdict(self)
        items = self._to_dict(data_dict, ignore_falsy)

        if data_key:
            items = {data_key: items}
        return items


@dataclass
class AtlasNames:
    """
    Custom implementation
    """
    name: Optional[str] = None
    qualifiedName: Optional[str] = None


@dataclass
class AtlasStruct:
    """
    http://atlas.apache.org/api/v2/json_AtlasStruct.html
    """
    attributes: Optional[Dict] = None
    typeName: Optional[str] = None


@dataclass
class AtlasObjectId:
    """
    Reference to an object-instance of an Atlas type - like entity.
    http://atlas.apache.org/api/v2/json_AtlasObjectId.html
    """
    guid: Optional[str] = None
    typeName: Optional[str] = None
    uniqueAttributes: Optional[Dict] = None


@dataclass
class AtlasRelatedCategoryHeader:
    """
    AtlasRelatedCategoryHeader
    """
    categoryGuid: Optional[str] = None
    description: Optional[str] = None
    displayText: Optional[str] = None
    parentCategoryGuid: Optional[str] = None
    relationGuid: Optional[str] = None


@dataclass
class AtlasRelatedTermHeader:
    """
    http://atlas.apache.org/api/v2/json_AtlasRelatedTermHeader.html
    """
    termGuid: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    displayText: Optional[str] = None
    expression: Optional[str] = None
    relationGuid: Optional[str] = None
    source: Optional[str] = None


@dataclass
class AtlasRelatedObjectId(AtlasBaseModelObject, AtlasObjectId):
    """
    http://atlas.apache.org/api/v2/json_AtlasRelatedObjectId.html
    """
    displayText: Optional[str] = None
    entityStatus: Optional[str] = None
    relationshipAttributes: Optional[AtlasStruct] = None
    relationshipGuid: Optional[str] = None
    relationshipStatus: Optional[str] = None
    relationshipType: Optional[str] = None

    @property
    def is_active_relation(self) -> bool:
        return self.entityStatus == Status.ACTIVE and self.relationshipStatus == Status.ACTIVE


@dataclass
class AtlasTermCategorizationHeader:
    """
    http://atlas.apache.org/api/v2/json_AtlasTermCategorizationHeader.html
    """
    categoryGuid: Optional[str] = None
    description: Optional[str] = None
    displayText: Optional[str] = None
    relationGuid: Optional[str] = None
    status: Optional[str] = None
