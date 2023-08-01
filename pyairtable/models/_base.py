from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Iterable, Optional

import inflection

if TYPE_CHECKING:  # mypy really does not like this conditional import.
    import pydantic
else:
    # Pydantic v2 broke a bunch of stuff. Luckily they provide a built-in v1.
    try:
        import pydantic.v1 as pydantic
    except ImportError:
        import pydantic

from typing_extensions import Self as SelfType


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

        # We'll assume this in a couple different places
        underscore_attrs_are_private = True


class SerializableModel(AirtableModel):
    """
    Base model for any data structures that can be saved back to the API.
    """

    #: Subclasses can set ``__writable__`` to define specific fields to write to the API.
    __writable__: ClassVar[Optional[Iterable[str]]] = None

    #: Subclasses can set ``__readonly__`` to define certain fields that should not be written to API.
    __readonly__: ClassVar[Optional[Iterable[str]]] = None

    _api: "pyairtable.api.api.Api"
    _url: str
    _deleted: bool = False

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
        if self._deleted:
            raise RuntimeError("save() called after delete()")
        include = set(self.__writable__) if self.__writable__ else None
        exclude = set(self.__readonly__) if self.__readonly__ else None
        data = self.dict(by_alias=True, include=include, exclude=exclude)
        response = self._api.request("PATCH", self._url, json=data)
        copyable = self.parse_obj(response)
        self.__dict__.update(copyable.__dict__)

    def delete(self) -> None:
        """
        Delete the record on the server and marks this instance as deleted.
        """
        response = self._api.request("DELETE", self._url)
        self._deleted = bool(response["deleted"])

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
            if self.__readonly__ and name in self.__readonly__:
                raise AttributeError(name)
            if self.__writable__ is not None and name not in self.__writable__:
                raise AttributeError(name)

        super().__setattr__(name, value)


import pyairtable.api.api  # noqa
