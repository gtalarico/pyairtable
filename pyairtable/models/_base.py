from functools import partial
from typing import Any, ClassVar, Iterable, Mapping, Optional, Set, Type, Union

import inflection
from typing_extensions import Self as SelfType

from pyairtable._compat import pydantic


class AirtableModel(pydantic.BaseModel):
    """
    Base model for any data structures that will be loaded from the Airtable API.
    """

    class Config:
        # Ignore field names we don't recognize, so applications don't crash
        # if Airtable decides to add new attributes.
        extra = "ignore"

        # Convert e.g. "base_invite_links" to "baseInviteLinks" for (de)serialization
        alias_generator = partial(inflection.camelize, uppercase_first_letter=False)

        # Allow both base_invite_links= and baseInviteLinks= in constructor
        allow_population_by_field_name = True

        # We'll assume this in a couple different places
        underscore_attrs_are_private = True

    _raw: Any = pydantic.PrivateAttr()

    @classmethod
    def parse_obj(cls, obj: Any) -> SelfType:
        instance = super().parse_obj(obj)
        instance._raw = obj
        return instance


class SerializableModel(AirtableModel):
    """
    Base model for any data structures that can be saved back to the API.

    Subclasses can pass a number of keyword arguments to control serialization behavior:

        * ``writable=``: field names that should be written to API on ``save()``.
        * ``readonly=``: field names that should not be written to API on ``save()``.
        * ``allow_update=``: boolean indicating whether to allow ``save()`` (default: true)
        * ``allow_delete=``: boolean indicating whether to allow ``delete()`` (default: true)
    """

    __writable: ClassVar[Optional[Iterable[str]]]
    __readonly: ClassVar[Optional[Iterable[str]]]
    __allow_update: ClassVar[bool]
    __allow_delete: ClassVar[bool]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        # These are private to SerializableModel
        if "writable" in kwargs and "readonly" in kwargs:
            raise ValueError("incompatible kwargs 'writable' and 'readonly'")
        cls.__writable = kwargs.get("writable")
        cls.__readonly = kwargs.get("readonly")
        cls.__allow_update = bool(kwargs.get("allow_update", True))
        cls.__allow_delete = bool(kwargs.get("allow_delete", True))

    _api: "pyairtable.api.api.Api" = pydantic.PrivateAttr()
    _url: str = pydantic.PrivateAttr()
    _deleted: bool = pydantic.PrivateAttr(default=False)

    @classmethod
    def from_api(cls, api: "pyairtable.api.api.Api", url: str, obj: Any) -> SelfType:
        """
        Constructs an instance which is able to update itself using an
        :class:`~pyairtable.Api`.

        Args:
            api: The connection to use for saving updates.
            url: The URL which can receive PATCH or DELETE requests for this object.
            obj: The JSON data structure used to construct the instance.
                 Will be passed to `parse_obj <https://docs.pydantic.dev/latest/usage/models/#helper-functions>`_.
        """
        parsed = cls.parse_obj(obj)
        parsed._api = api
        parsed._url = url
        return parsed

    def save(self) -> None:
        """
        Save any changes made to the instance's writable fields.

        Will raise ``RuntimeError`` if the record has been deleted.
        """
        if not self.__allow_update:
            raise NotImplementedError(f"{self.__class__.__name__}.save() not allowed")
        if self._deleted:
            raise RuntimeError("save() called after delete()")
        include = set(self.__writable) if self.__writable else None
        exclude = set(self.__readonly) if self.__readonly else None
        data = self.dict(by_alias=True, include=include, exclude=exclude)
        response = self._api.request("PATCH", self._url, json=data)
        copyable = self.parse_obj(response)
        self.__dict__.update(copyable.__dict__)

    def delete(self) -> None:
        """
        Delete the record on the server and marks this instance as deleted.
        """
        if not self.__allow_delete:
            raise NotImplementedError(f"{self.__class__.__name__}.delete() not allowed")
        self._api.request("DELETE", self._url)
        self._deleted = True

    @property
    def deleted(self) -> bool:
        """
        Indicates whether the record has been deleted since being returned from the API.
        """
        return self._deleted

    def __setattr__(self, name: str, value: Any) -> None:
        # Prevents implementers from changing values on readonly or non-writable fields.
        # Mypy can't tell that we are using pydantic v1.
        if name in self.__class__.__fields__:  # type: ignore[operator, unused-ignore]
            if self.__readonly and name in self.__readonly:
                raise AttributeError(name)
            if self.__writable is not None and name not in self.__writable:
                raise AttributeError(name)

        super().__setattr__(name, value)


def update_forward_refs(
    obj: Union[Type[AirtableModel], Mapping[str, Any]],
    memo: Optional[Set[int]] = None,
) -> None:
    """
    Convenience method to ensure we update forward references for all nested models.

    Any time a type annotation refers to a nested class that isn't present
    at the time the attribute is created, we need to tell pydantic to
    update forward references after all the referenced models exist.

    Only intended for use within pyAirtable, like:

        >>> from pyairtable.models._base import AirtableModel, update_forward_refs
        >>> class A(AirtableModel): ...
        >>> class B(AirtableModel): ...
        ...     class B_One(AirtableModel): ...
        ...     class B_Two(AirtableModel): ...
        >>> update_forward_refs(vars())
    """
    # Avoid infinite circular loops
    memo = set() if memo is None else memo
    # If it's a type, update its refs, then do the same for any nested classes.
    # This will raise AttributeError if given a non-AirtableModel type.
    if isinstance(obj, type):
        if id(obj) in memo:
            return
        memo.add(id(obj))
        obj.update_forward_refs()
        return update_forward_refs(vars(obj), memo=memo)
    # If it's a mapping, update refs for any AirtableModel instances.
    for value in obj.values():
        if isinstance(value, type) and issubclass(value, AirtableModel):
            update_forward_refs(value, memo=memo)


import pyairtable.api.api  # noqa
