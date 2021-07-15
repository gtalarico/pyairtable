from airtable import Table
from typing import TypeVar, Type, Generic

from .fields import FieldDescriptor

T = TypeVar("T", bound="Model")


class Model:

    id: str = ""
    created_time: str = ""
    _fields: dict
    _table: Table

    class Meta:
        base_id: str
        table_name: str
        api_key: str
        timeout = None
        typecast = True

    def __init__(self, **kwargs):
        # To Store Fields
        self._fields = {}

        # Get descriptors values
        descriptor_fields = {
            k: v
            for k, v in self.__class__.__dict__.items()
            if isinstance(v, FieldDescriptor)
        }

        # Set descriptors values
        for key, value in kwargs.items():
            if key not in descriptor_fields:
                msg = "invalid kwarg '{}'".format(key)
                raise ValueError(msg)
            setattr(self, key, value)

        # Verify required Meta attributes were set
        if not getattr(self.Meta, "base_id", None):
            raise ValueError("Meta.base_id must be defined in model")
        if not getattr(self.Meta, "table_name", None):
            raise ValueError("Meta.table_name must be defined in model")
        if not getattr(self.Meta, "api_key", None):
            raise ValueError("Meta.api_key must be defined in model")

        # Set default Meta values
        self.Meta.timeout = getattr(self.Meta, "timeout", Model.Meta.timeout)
        self.Meta.typecast = getattr(self.Meta, "typecast", Model.Meta.typecast)

    def exists(self) -> bool:
        return bool(self.id)

    @classmethod
    def get_table(cls) -> Table:
        """ return airtable class instance, instantiate one if needed """
        if not hasattr(cls, "_table"):
            cls._table = Table(
                cls.Meta.base_id,
                cls.Meta.table_name,
                api_key=cls.Meta.api_key,
                timeout=cls.Meta.timeout,
            )
        return cls._table

    def save(self) -> bool:
        table = self.get_table()
        typecast = self.Meta.typecast
        if not self.id:
            record = table.create(self._fields, typecast=typecast)
            did_create = True
        else:
            record = table.update(
                self.id, self._fields, replace=True, typecast=typecast
            )
            did_create = False
        self.id = record["id"]
        self.created_time = record["createdTime"]
        return did_create

    def delete(self) -> bool:
        if not self.id:
            raise ValueError("cannot be deleted because it does not have id")
        table = self.get_table()
        result = table.delete(self.id)
        # Is it even possible go get "deleted" False?
        return result["deleted"]

    def to_record(self) -> dict:
        return {"id": self.id, "createdTime": self.created_time, "fields": self._fields}

    @classmethod
    def from_record(cls: Type[T], record: dict) -> T:
        """ create entity instance a record (API dict response) """
        instance = cls()
        instance._fields = record["fields"]
        instance.created_time = record["createdTime"]
        instance.id = record["id"]
        return instance

    @classmethod
    def from_id(cls: Type[T], record_id: str) -> T:
        table = cls.get_table()
        record = table.get(record_id)
        return cls.from_record(record)

    def reload(self):
        if not self.id:
            raise ValueError("cannot be deleted because it does not have id")

        record = self.get_table().get(self.id)
        self._fields = record["fields"]
        self.created_time = record["createdTime"]
