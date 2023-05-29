"""
The :class:`Model` class allows you create an orm-style class for your
Airtable tables.

>>> from pyairtable.orm import Model, fields
>>> class Contact(Model):
...     first_name = fields.TextField("First Name")
...     last_name = fields.TextField("Last Name")
...     email = fields.EmailField("Email")
...     is_registered = fields.CheckboxField("Registered")
...     company = fields.LinkField("Company", Company, lazy=False)
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
'rec123asa23'


You can read and modify attributes. If record already exists,
:meth:`~pyairtable.orm.model.Model.save` will update the record:

>>> assert contact.is_registered is False
>>> contact.save()
>>> assert contact.is_registered is True
>>> contact.to_record()
{
    "id": "recS6qSLw0OCA6Xul",
    "createdTime": "2021-07-14T06:42:37.000Z",
    "fields": {
        "First Name": "Mike",
        "Last Name": "McDonalds",
        "Email": "mike@mcd.com",
        "Registered": True
    }
}

Finally, you can use :meth:`~pyairtable.orm.model.Model.delete` to delete the record:

>>> contact.delete()
True
"""
import abc
from typing import Any, Dict, List, Optional

from typing_extensions import Self as SelfType

from pyairtable.api.table import Table
from pyairtable.api.types import FieldName, RecordDict, RecordId
from pyairtable.orm.fields import AnyField, Field


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
    _fields: Dict[FieldName, Any] = {}
    _linked_cache: Dict[RecordId, SelfType] = {}

    def __init_subclass__(cls, **kwargs: Any):
        cls._validate_class()
        super().__init_subclass__(**kwargs)

    @classmethod
    def _attribute_descriptor_map(cls) -> Dict[str, AnyField]:
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
    def _field_name_descriptor_map(cls) -> Dict[FieldName, AnyField]:
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
    def _field_name_attribute_map(cls) -> Dict[FieldName, str]:
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

    def __init__(self, **fields: Any):
        # To Store Fields
        self._fields = {}

        # Set descriptors
        for key, value in fields.items():
            if key not in self._attribute_descriptor_map():
                raise AttributeError(key)
            setattr(self, key, value)

        self.typecast = bool(self._get_meta("typecast", default=True))

    @classmethod
    def _get_meta(cls, name: str, default: Any = None, required: bool = False) -> Any:
        if not hasattr(cls, "Meta"):
            raise AttributeError(f"{cls.__name__}.Meta must be defined")
        if required and not hasattr(cls.Meta, name):
            raise ValueError(f"{cls.__name__}.Meta.{name} must be defined")
        value = getattr(cls.Meta, name, default)
        if required and value is None:
            raise ValueError(f"{cls.__name__}.Meta.{name} cannot be None")
        return value

    @classmethod
    def _validate_class(cls) -> None:
        # Verify required Meta attributes were set
        assert cls._get_meta("api_key", required=True)
        assert cls._get_meta("base_id", required=True)
        assert cls._get_meta("table_name", required=True)

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
                cls._get_meta("api_key"),
                cls._get_meta("base_id"),
                cls._get_meta("table_name"),
                timeout=cls._get_meta("timeout"),
            )
        return cls._table

    def exists(self) -> bool:
        """Returns boolean indicating if instance exists (has 'id' attribute)"""
        return bool(self.id)

    def save(self) -> bool:
        """
        Saves or updates a model.
        If instance has no 'id', it will be created, otherwise updated.

        Returns `True` if was created and `False` if it was updated
        """
        table = self.get_table()
        record = self.to_record(only_writable=True)
        fields = record["fields"]

        if not self.id:
            record = table.create(fields, typecast=self.typecast)
            did_create = True
        else:
            record = table.update(self.id, fields, typecast=self.typecast)
            did_create = False

        self.id = record["id"]
        self.created_time = record["createdTime"]
        return did_create

    def delete(self) -> bool:
        """Deletes record. Must have 'id' field"""
        if not self.id:
            raise ValueError("cannot be deleted because it does not have id")
        table = self.get_table()
        result = table.delete(self.id)
        # Is it even possible to get "deleted" False?
        return bool(result["deleted"])

    @classmethod
    def all(cls, **kwargs: Any) -> List[SelfType]:
        """
        Returns all records for this model. For the full list of
        keyword arguments, see :meth:`~pyairtable.api.Api.all`
        """
        table = cls.get_table()
        return [cls.from_record(record) for record in table.all(**kwargs)]

    @classmethod
    def first(cls, **kwargs: Any) -> Optional[SelfType]:
        """
        Returns the first record for this model. For the full list of
        keyword arguments, see :meth:`~pyairtable.api.Api.all`
        """
        table = cls.get_table()
        if record := table.first(**kwargs):
            return cls.from_record(record)
        return None

    def to_record(self, only_writable: bool = False) -> RecordDict:
        """
        Returns a dictionary object as an Airtable record.
        This method converts internal field values into values expected by Airtable.
        e.g. a ``datetime`` value from :class:``DateTimeField`` is converted into an
        ISO 8601 string

        Args:
            only_writable: If ``True``, the result will exclude any
                values which are associated with readonly fields.
        """
        map_ = self._field_name_descriptor_map()
        fields = {
            field: map_[field].to_record_value(value)
            for field, value in self._fields.items()
            if not (map_[field].readonly and only_writable)
        }
        return {"id": self.id, "createdTime": self.created_time, "fields": fields}

    @classmethod
    def from_record(cls, record: RecordDict) -> SelfType:
        """Create instance from record dictionary"""
        name_field_map = cls._field_name_descriptor_map()
        # Convert Column Names into model field names
        field_values = {
            # Use field's to_internal_value to cast into model fields
            field: name_field_map[field].to_internal_value(value)
            for (field, value) in record["fields"].items()
            # Silently proceed if Airtable returns fields we don't recognize
            if field in name_field_map
        }
        # Since instance(**field_values) will perform validation and fail on
        # any readonly fields, so instead we directly set instance._fields.
        instance = cls()
        instance._fields = field_values
        instance.created_time = record["createdTime"]
        instance.id = record["id"]
        return instance

    @classmethod
    def from_id(cls, record_id: str, fetch: bool = True) -> SelfType:
        """
        Create an instance from a `record_id`

        Args:
            record_id: |arg_record_id|
            fetch: If `True`, record will be fetched and fields will be
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

    def fetch(self) -> None:
        """Fetches field and resets instance field values from the Airtable record"""
        if not self.id:
            raise ValueError("cannot be fetched because instance does not have an id")

        updated = self.from_id(self.id, fetch=True)
        self._fields = updated._fields
        self.created_time = updated.created_time

    def __repr__(self) -> str:
        return "<Model={} {}>".format(self.__class__.__name__, hex(id(self)))
