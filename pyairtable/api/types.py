"""
Types and TypedDicts for pyAirtable.
"""
from functools import lru_cache
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar, Union, cast

import pydantic
from typing_extensions import Required, TypeAlias, TypedDict

T = TypeVar("T")
RecordId: TypeAlias = str
Timestamp: TypeAlias = str
FieldName: TypeAlias = str


class AttachmentDict(TypedDict, total=False):
    """
    A dict representing an attachment stored in an Attachments field.

    >>> record = api.get('base_id', 'table_name', 'recW8eG2x0ew1Af')
    >>> record['fields']['Attachments']
    [
        {
            'id': 'attW8eG2x0ew1Af',
            'url': 'https://example.com/hello.jpg',
            'filename': 'hello.jpg'
        }
    ]

    See https://airtable.com/developers/web/api/field-model#multipleattachment
    """

    id: Required[str]
    url: Required[str]
    type: str
    filename: str
    size: int
    height: int
    width: int
    thumbnails: Dict[str, Dict[str, Union[str, int]]]


class CreateAttachmentDict(TypedDict, total=False):
    """
    A dict representing a new attachment to be written to the Airtable API.
    """

    url: Required[str]
    filename: str


class BarcodeDict(TypedDict, total=False):
    """
    A dict representing the value stored in a Barcode field.

    >>> record = api.get('base_id', 'table_name', 'recW8eG2x0ew1Af')
    >>> record['fields']['Barcode']
    {'type': 'upce', 'text': '01234567'}

    See https://airtable.com/developers/web/api/field-model#barcode
    """

    type: str
    text: Required[str]


class ButtonDict(TypedDict):
    """
    A dict representing the value stored in a Button field.

    >>> record = api.get('base_id', 'table_name', 'recW8eG2x0ew1Af')
    >>> record['fields']['Click Me']
    {'label': 'Click Me', 'url': 'http://example.com'}

    See https://airtable.com/developers/web/api/field-model#button
    """

    label: str
    url: Optional[str]


class CollaboratorDict(TypedDict, total=False):
    """
    A dict representing the value stored in a User field.

    >>> record = api.get('base_id', 'table_name', 'recW8eG2x0ew1Af')
    >>> record['fields']['Created By']
    {
        'id': 'usrAdw9EjV90xbW',
        'email': 'alice@example.com',
        'name': 'Alice Arnold'
    }
    >>> record['fields']['Collaborators']
    [
        {
            'id': 'usrAdw9EjV90xbW',
            'email': 'alice@example.com',
            'name': 'Alice Arnold'
        },
        {
            'id': 'usrAdw9EjV90xbX',
            'email': 'bob@example.com',
            'name': 'Bob Barker'
        }
    ]

    See https://airtable.com/developers/web/api/field-model#collaborator
    """

    id: Required[str]
    email: str
    name: str
    profilePicUrl: str


#: Represents the value of a field, excluding lists of values.
RawFieldValue: TypeAlias = Union[
    str,
    int,
    float,
    bool,
    CollaboratorDict,
    BarcodeDict,
    ButtonDict,
]


#: Represents the value of a field on a particular record.
FieldValue: TypeAlias = Union[
    str,
    int,
    float,
    bool,
    CollaboratorDict,
    BarcodeDict,
    ButtonDict,
    List[str],
    List[int],
    List[float],
    List[bool],
    List[AttachmentDict],
    List[CollaboratorDict],
]


#: A mapping of field names to values.
Fields: TypeAlias = Dict[FieldName, FieldValue]


class RecordDict(TypedDict):
    """
    Represents a record returned from the Airtable API.
    """

    id: RecordId
    createdTime: Timestamp
    fields: Fields


class CreateRecordDict(TypedDict):
    """
    Represents the payload passed to the Airtable API to create a record.
    """

    fields: Fields


class UpdateRecordDict(TypedDict):
    """
    Represents the payload passed to the Airtable API to create a record.
    """

    id: RecordId
    fields: Fields


class RecordDeletedDict(TypedDict):
    """
    Represents the payload passed to the Airtable API to create a record.
    """

    id: RecordId
    deleted: Literal[True]


@lru_cache
def _create_model_from_typeddict(cls: Type[T]) -> Type[pydantic.BaseModel]:
    """
    Creates a pydantic model from a TypedDict to use as a validator.
    Memoizes the result so we don't have to call this more than once per class.
    """
    return pydantic.create_model_from_typeddict(cls)


def assert_typed_dict(cls: Type[T], obj: Any) -> T:
    """
    Raises a TypeError if the given object is not an instance of the given TypedDict.

    Args:
        cls: The TypedDict class.
        obj: The object that should be a TypedDict.
    """
    if not isinstance(obj, dict):
        raise TypeError(f"expected dict, got {type(obj)}")
    # mypy complains cls isn't Hashable, but it is; see https://github.com/python/mypy/issues/2412
    model = _create_model_from_typeddict(cls)  # type: ignore
    try:
        model(**obj)
    except pydantic.ValidationError:
        raise TypeError(f"dict with keys {sorted(obj)} is not {cls.__name__}")
    return cast(T, obj)


def assert_typed_dicts(cls: Type[T], objects: Any) -> List[T]:
    """
    Raises a TypeError if the given object is not a list of dicts where
    each is an instance of the given TypedDict.

    Args:
        cls: The TypedDict class.
        objects: The object that should be a list of TypedDicts.
    """
    if not isinstance(objects, list):
        raise TypeError(f"expected list, got {type(objects)}")
    return [assert_typed_dict(cls, obj) for obj in objects]
