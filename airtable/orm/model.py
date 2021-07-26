"""
The :any:`orm.Model` class allows you create an orm-style class for your
Airtable tables.


Example
*******

Model Definition

>>> from airtable.orm import Model, fields
>>> class Contact(Model):
...     first_name = fields.TextField("First Name")
...     last_name = fields.TextField("Last Name")
...     email = fields.EmailField("Email")
...     is_registered = fields.CheckboxField("Registered")
...     partner = fields.LinkField("Partner", "Contact", lazy=False)
...
...     class Meta:
...         base_id = "appaPqizdsNHDvlEm"
...         table_name = "Contact"
...         api_key = "keyapikey"


Model Usage

>>> contact = Contact(
...     first_name="Mike",
...     last_name="McDonalds",
...     email="mike@mcd.com",
...     is_registered=False
... )
>>> assert contact.id is None
>>> assert contact.is_registered = True
>>> assert contact.save()
>>> assert contact.id
rec123asa23

>>> contact.delete()
```

Fields
******

Simple
-------

TODO

Linked
-------

TODO

"""

from airtable import Table
from typing import TypeVar, Type, Optional, Tuple

from .fields import Field

T = TypeVar("T", bound="Model")


class Model:

    id: str = ""
    created_time: str = ""
    _fields: dict
    _linked_cache: dict
    _table: Table

    class Meta:
        base_id: str
        table_name: str
        api_key: str
        timeout: Optional[Tuple[int, int]]
        typecast: bool

    @classmethod
    def descriptor_fields(cls):
        """
        {
            "field_name": <TextField field_name="Field Name">,
            "another_Field": <NumberField field_name="Some Number">,
        }
        """
        return {k: v for k, v in cls.__dict__.items() if isinstance(v, Field)}

    @classmethod
    def descriptor_to_field_name_map(cls):
        return {v.field_name: k for k, v in cls.descriptor_fields().items()}
        # return {
        #     "Field Name": "street",
        #     "Street": ""
        #     # Docs
        # }

    def record_fields_to_kwargs(self):
        """{"fields": {"Street Name": "X"}} =>  { "street_name": "X" }"""

    def __init__(self, **fields):
        # To Store Fields
        self._fields = {}
        self._linked_cache = {}

        # Get descriptors values
        # TODO check for clashes
        # disallowed_names = ("id", "crreated_time", "_fields", "_linked_cache", "_table")

        # Set descriptors values
        for key, value in fields.items():
            if key not in self.descriptor_fields():
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

        self.typecast = getattr(self.Meta, "typecast", True)

    def exists(self) -> bool:
        """Returns boolean indicating if instance exists (has 'id' attribute)"""
        return bool(self.id)

    @classmethod
    def get_table(cls) -> Table:
        """Return Airtable :any:`Table` class instance"""
        if not hasattr(cls, "_table"):
            cls._table = Table(
                cls.Meta.base_id,
                cls.Meta.table_name,
                api_key=cls.Meta.api_key,
                timeout=getattr(cls.Meta, "timeout", None),
            )
        return cls._table

    def save(self) -> bool:
        """
        Saves or updates a model.
        If instance has no 'id', it will be created, otherwise updatedself.

        Returns `True` if was created and `False` if it was updated
        """
        table = self.get_table()
        if not self.id:
            record = table.create(self._fields, typecast=self.typecast)
            did_create = True
        else:
            record = table.update(
                self.id, self._fields, replace=True, typecast=self.typecast
            )
            did_create = False
        self.id = record["id"]
        self.created_time = record["createdTime"]
        return did_create

    def delete(self) -> bool:
        """Deleted record. Must have 'id' field"""
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
        """Create instance from record dictionary"""
        map_ = cls.descriptor_to_field_name_map()
        try:
            # Convert Column Names into model field names
            kwargs = {map_[k]: v for k, v in record["fields"].items()}
        except KeyError as exc:
            raise ValueError("Invalid Field Name: {} for model {}".format(exc, cls))
        instance = cls(**kwargs)
        instance.created_time = record["createdTime"]
        instance.id = record["id"]
        return instance

    @classmethod
    def from_id(cls: Type[T], record_id: str, fetch=True) -> T:
        """
        Create an instance from a `record_id`

        Args:
            record_id: |arg_record_id|

        Keyward Args:
            fetch: If `True`, record will be fetched from airtable and fields will be
                updated. If `False`, a new instance is created with the provided `id`,
                but field values are unset. Default is `True`.

        """
        if fetch:
            table = cls.get_table()
            record = table.get(record_id)
            return cls.from_record(record)
        else:
            instance = cls()
            instance.id = record_id
            return instance

    def reload(self):
        """Fetches field and resets instance field values from airtable record"""
        if not self.id:
            raise ValueError("cannot be deleted because it does not have id")

        record = self.get_table().get(self.id)
        self._fields = record["fields"]
        self.created_time = record["createdTime"]

    def __repr__(self):
        return "<Model={}>".format(self.__class__.__name__)
