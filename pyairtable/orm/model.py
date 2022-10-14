"""
The :class:`Model` class allows you create an orm-style class for your
Airtable tables.

>>> from pyairtable.orm import Model, fields
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


Once you have a class, you can create new objects to represent your
Airtable records. Call :meth:`~pyairtable.orm.model.Model.save` to create a new record.

>>> contact = Contact(
...     first_name="Mike",
...     last_name="McDonalds",
...     email="mike@mcd.com",
...     is_registered=False
... )
...
>>> assert contact.id is None
>>> contact.exists()
False
>>> assert contact.save()
>>> contact.exists()
True
>>> contact.id
rec123asa23


You can read and modify attributes. If record already exists,
:meth:`~pyairtable.orm.model.Model.save` will update the record:

>>> assert contact.is_registered is False
>>> contact.save()
>>> assert contact.is_registered is True
>>> contact.to_record()
{
    "id": recS6qSLw0OCA6Xul",
    "createdTime": "2021-07-14T06:42:37.000Z",
    "fields": {
        "First Name": "Mike",
        "Last Name": "McDonalds",
        "Email": "mike@mcd.com",
        "Resgistered": True
    }
}

Finally, you can use :meth:`~pyairtable.orm.model.Model.delete` to delete the record:

>>> contact.delete()
True

"""
import abc
from pyairtable import Table
from typing import TypeVar, Type, List

from .fields import Field

T = TypeVar("T", bound="Model")


class Model(metaclass=abc.ABCMeta):
    """
    This class allows you create an orm-style class for your Airtable tables.

    This is a meta class and can only be used to define sub-classes.

    The ``Meta`` is reuired and must specify all three attributes: ``base_id``,
    ``table_id``, and ``api_key``.

    >>> from pyairtable.orm import Model, fields
    >>> class Contact(Model):
    ...     first_name = fields.TextField("First Name")
    ...     age = fields.IntegerField("Age")
    ...
    ...     class Meta:
    ...         base_id = "appaPqizdsNHDvlEm"
    ...         table_name = "Contact"
    ...         api_key = "keyapikey"
    ...         timeout: Optional[Tuple[int, int]] = (5, 5)
    ...         typecast: bool = True
    """

    id: str = ""
    created_time: str = ""
    _table: Table
    _fields: dict = {}
    _linked_cache: dict = {}

    def __init_subclass__(cls, **kwargs):
        cls._validate_class()
        super().__init_subclass__(**kwargs)

    @classmethod
    def _attribute_descriptor_map(cls):
        """
        Returns a dictionary mapping the model's attribute names to the field's

        >>> class Test(Model):
        ...     first_name = TextField("First Name")
        ...     age = NumberField("Age")
        ...
        >>> Test._attribute_descriptor_map()
        >>> {
        ...     "field_name": <TextField field_name="First Name">,
        ...     "another_Field": <NumberField field_name="Age">,
        ... }
        """
        return {k: v for k, v in cls.__dict__.items() if isinstance(v, Field)}

    @classmethod
    def _field_name_descriptor_map(cls):
        """
        Returns a dictionary that maps Fields 'Names' to descriptor fields

        >>> class Test(Model):
        ...     first_name = TextField("First Name")
        ...     age = NumberField("Age")
        ...
        >>> Test._field_name_descriptor_map()
        >>> {
        ...     "First Name": <TextField field_name="First Name">,
        ...     "Age": <NumberField field_name="Age">,
        ... }
        """
        return {f.field_name: f for f in cls._attribute_descriptor_map().values()}

    @classmethod
    def _field_name_attribute_map(cls):
        """
        Returns a dictionary that maps Fields 'Names' to the model attribute name:

        >>> class Test(Model):
        ...     first_name = TextField("First Name")
        ...     age = NumberField("Age")
        ...
        >>> Test._field_name_attribute_map()
        >>> {
        ...     "First Name": "first_name"
        ...     "Age": "age"
        ... }
        """
        return {v.field_name: k for k, v in cls._attribute_descriptor_map().items()}

    def __init__(self, **fields):
        # To Store Fields
        self._fields = {}

        # Set descriptors
        for key, value in fields.items():
            if key not in self._attribute_descriptor_map():
                msg = "invalid kwarg '{}'".format(key)
                raise ValueError(msg)
            setattr(self, key, value)

        self.typecast = getattr(self.Meta, "typecast", True)

    @classmethod
    def _validate_class(cls):
        # Verify required Meta attributes were set
        if not getattr(cls.Meta, "base_id", None):
            raise ValueError("Meta.base_id must be defined in model")
        if not getattr(cls.Meta, "table_name", None):
            raise ValueError("Meta.table_name must be defined in model")
        if not getattr(cls.Meta, "api_key", None):
            raise ValueError("Meta.api_key must be defined in model")

        model_attributes = [a for a in cls.__dict__.keys() if not a.startswith("__")]
        overridden = set(model_attributes).intersection(Model.__dict__.keys())
        if overridden:
            raise ValueError(
                "Class {cls} fields clash with existing method: {name}".format(
                    cls=cls.__name__, name=overridden
                )
            )

    @classmethod
    def get_table(cls) -> Table:
        """Return Airtable :class:`~pyairtable.api.Table` class instance"""
        if not hasattr(cls, "_table"):
            cls._table = Table(
                cls.Meta.api_key,  # type: ignore
                cls.Meta.base_id,  # type: ignore
                cls.Meta.table_name,  # type: ignore
                timeout=getattr(cls.Meta, "timeout", None),  # type: ignore
            )
        return cls._table

    def exists(self) -> bool:
        """Returns boolean indicating if instance exists (has 'id' attribute)"""
        return bool(self.id)

    def save(self) -> bool:
        """
        Saves or updates a model.
        If instance has no 'id', it will be created, otherwise updatedself.

        Returns `True` if was created and `False` if it was updated
        """
        table = self.get_table()
        record = self.to_record()
        fields = record["fields"]

        if not self.id:
            record = table.create(fields, typecast=self.typecast)
            did_create = True
        else:
            record = table.update(self.id, fields, replace=True, typecast=self.typecast)
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

    @classmethod
    def all(cls, **kwargs) -> List[T]:
        """Returns all records for this model. See :meth:`~pyairtable.api.Api.all`"""
        table = cls.get_table()
        return table.all(**kwargs)

    @classmethod
    def first(cls, **kwargs) -> List[T]:
        """Returns first record for this model. See :meth:`~pyairtable.api.Api.first`"""
        table = cls.get_table()
        return table.first(**kwargs)

    def to_record(self) -> dict:
        """
        Returns a dictionary object as an Airtable record.
        This method converts internal field values into values expected by Airtable.
        e.g. a ``datetime`` value from :class:``DateTimeField`` is converted into an
        ISO 8601 string
        """
        map_ = self._field_name_descriptor_map()
        fields = {k: map_[k].to_record_value(v) for k, v in self._fields.items()}
        return {"id": self.id, "createdTime": self.created_time, "fields": fields}

    @classmethod
    def from_record(cls: Type[T], record: dict) -> T:
        """Create instance from record dictionary"""
        name_attr_map = cls._field_name_attribute_map()
        name_field_map = cls._field_name_descriptor_map()
        try:
            # Convert Column Names into model field names
            # Use field's to_internal to cast into model fields
            kwargs = {
                name_attr_map[k]: name_field_map[k].to_internal_value(v)
                for k, v in record["fields"].items()
            }
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
            fetch: If `True`, record will be fetched and fields will be
                updated. If `False`, a new instance is created with the provided `id`,
                but field values are unset. Default is `True`.

        Returns:
            (``Model``): Instance of model
        """
        if fetch:
            table = cls.get_table()
            record = table.get(record_id)
            return cls.from_record(record)
        else:
            instance = cls()
            instance.id = record_id
            return instance

    def fetch(self):
        """Fetches field and resets instance field values from the Airtable record"""
        if not self.id:
            raise ValueError("cannot be fetched because instance does not have an id")

        updated = self.from_id(self.id, fetch=True)
        self._fields = updated._fields
        self.created_time = updated.created_time

    def __repr__(self):
        return "<Model={} {}>".format(self.__class__.__name__, hex(id(self)))

    # TODO - see metadata.py
    # def verify_schema(cls) -> Tuple[bool, dict]:
    #     """verify local airtable models"""

    #     base_list = cls.get_base_list()
    #     base_id_exists = cls.base_id in [b["id"] for b in base_list["bases"]]

    #     if base_id_exists:
    #         base_schema = cls.get_base_schema()
    #         table_schema: dict = next(
    #             (t for t in base_schema["tables"] if t["name"] == cls.table_name), {}
    #         )
    #         table_exists = bool(table_schema)
    #     else:
    #         table_exists = False

    #     if table_exists:
    #         airtable_field_names = [f["name"] for f in table_schema["fields"]]
    #         # Fields.NAME = "|NAME|", Fields.ID = "|ID|") -> ["|NAME|", "|ID|"]
    #         local_field_names = [v for k, v in vars(cls.Fields).items() if k.isupper()]
    #         fields = {n: n in airtable_field_names for n in local_field_names}
    #     else:
    #         fields = {}

    #     in_sync = base_id_exists and table_exists and all(fields.values())
    #     details = {"base": base_id_exists, "table": table_exists, "fields": fields}
    #     return (in_sync, details)
