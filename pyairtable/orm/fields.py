"""
Field are used to define the Airtable column type for your pyAirtable models.

Internally these are implemented as descriptors, this allows us to proxy getting and settings values,
while also providing a type-annotated interface.

>>> from pyairtable.orm import Model, fields
>>> class Contact(Model):
...     name = fields.TextField("Name")
...     is_registered = fields.CheckboxField("Registered")
...
...     class Meta:
...         ...
>>> contact = Contact(name="George", is_registered=True)
>>> assert contact.name == "George"
>>> reveal_type(contact.name)  # -> str
>>> contact.to_record()
{
    "id": recS6qSLw0OCA6Xul",
    "createdTime": "2021-07-14T06:42:37.000Z",
    "fields": {
        "Name": "George",
        "Registered": True,
    }
}


Link Fields
-----------

In addition to standard data type fields, the :class:`LinkField` class
offers a special behaviour that can fetch linked records.

In other words, you can transverse related records through their ``Link Fields``:

>>> from pyairtable.orm import Model, fields
>>> class Company(Model):
...     name = fields.TextField("Name")
...     class Meta:
...         ...
...
>>> class Person(Model):
...     company = fields.LinkField("Company", Company, lazy=False)
...     class Meta:
...         ...
...
>>> contact.from_id("recS6qSLw0OCA6Xul")
>>> contact.company.name # outputs value of Company.name attribute

-----------

"""
import abc
from datetime import date, datetime
from typing import (
    Any,
    TypeVar,
    Type,
    Generic,
    Optional,
    List,
    TYPE_CHECKING,
    Union,
)

from pyairtable import utils

if TYPE_CHECKING:
    from pyairtable.orm import Model  # noqa

T_Linked = TypeVar("T_Linked", bound="Model")


class Field(metaclass=abc.ABCMeta):
    def __init__(self, field_name, validate_type=True) -> None:
        self.field_name = field_name
        self.validate_type = True

    def __set_name__(self, owner, name):
        self.attribute_name = name

    def __get__(self, instance, cls=None):
        # Raise if descriptor is called on class, where instance is None
        if not instance:
            raise RuntimeError("cannot access descriptors on class")

        field_name = self.field_name
        try:
            # Field Field is not yet in dict, return None
            return instance._fields[field_name]
        except (KeyError, AttributeError):
            return None

    def __set__(self, instance, value):
        if not hasattr(instance, "_fields"):
            instance._fields = {}
        if self.validate_type:
            self.valid_or_raise(value)
        instance._fields[self.field_name] = value

    def to_record_value(self, value: Any) -> Any:
        return value

    def to_internal_value(self, value: Any) -> Any:
        return value

    def valid_or_raise(self, value) -> None:
        ...

    def __repr__(self):
        return "<{} field_name='{}'>".format(self.__class__.__name__, self.field_name)


class TextField(Field):
    """Airtable Single Text or Multiline Text Fields. Uses ``str`` to store value"""

    def to_internal_value(self, value: Any) -> str:
        return str(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, str):
            raise ValueError("TextField value must be 'str'")

    def __get__(self, *args, **kwargs) -> Optional[str]:
        return super().__get__(*args, **kwargs)


class ListFieldCustom(Field):
    """Airtable List field."""

    def to_record_value(self, value: Any) -> list:
        return list(value)

    def to_internal_value(self, value: list) -> list:
        return list(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, list):
            raise ValueError(f"ListField '{self.field_name}' value ({value}) must be a 'list'")

    def __get__(self, *args, **kwargs) -> Optional[list]:
        return super().__get__(*args, **kwargs)


class EmailField(TextField):
    """Airtable Email field. Uses ``str`` to store value"""

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, str):
            raise ValueError("EmailField value must be 'str'")


class IntegerField(Field):
    """Airtable Number field with Integer Precision. Uses ``int`` to store value"""

    def to_internal_value(self, value: Any) -> int:
        return int(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, int):
            raise ValueError("IntegerField value must be 'int'")

    def __get__(self, *args, **kwargs) -> Optional[int]:
        return super().__get__(*args, **kwargs)


class FloatField(Field):
    """Airtable Number field with Decimal precision. Uses ``float`` to store value"""

    def to_internal_value(self, value: Any) -> float:
        return float(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, float):
            raise ValueError("FloatField value must be 'float'")

    def __get__(self, *args, **kwargs) -> Optional[float]:
        return super().__get__(*args, **kwargs)


class CheckboxField(Field):
    """Airtable Checkbox field. Uses ``bool`` to store value"""

    def to_internal_value(self, value: Any) -> bool:
        return bool(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, bool):
            raise ValueError("CheckboxField value must be 'bool'")

    def __get__(self, *args, **kwargs) -> Optional[bool]:
        return super().__get__(*args, **kwargs)


class DatetimeField(Field):
    """Airtable Datetime field. Uses ``datetime`` to store value"""

    def to_record_value(self, value: datetime) -> str:
        """Airtable expects ISO 8601 string datetime eg. "2014-09-05T12:34:56.000Z" """
        return utils.datetime_to_iso_str(value)

    def to_internal_value(self, value: str) -> datetime:
        """Airtable returns ISO 8601 string datetime eg. "2014-09-05T07:00:00.000Z" """
        return utils.datetime_from_iso_str(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, datetime):
            raise ValueError("DatetimeField value must be 'datetime'")

    def __get__(self, *args, **kwargs) -> Optional[datetime]:
        return super().__get__(*args, **kwargs)


class DateField(Field):
    """Airtable Date field. Uses ``Date`` to store value"""

    def to_record_value(self, value: date) -> str:
        """Airtable expects ISO 8601 date string eg. "2014-09-05"""
        return utils.date_to_iso_str(value)

    def to_internal_value(self, value: str) -> date:
        """Airtable returns ISO 8601 date string eg. "2014-09-05"""
        return utils.date_from_iso_str(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, date):
            raise ValueError("DateField value must be 'date'")

    def __get__(self, *args, **kwargs) -> Optional[datetime]:
        return super().__get__(*args, **kwargs)


class LookupField(Field):
    """Airtable Lookup Fields. Uses ``list`` to store value"""

    def __init__(self, field_name, model: Union[str, Type[T_Linked]] = Field) -> None:

        if isinstance(model, str):
            model = cast(Type[T_Linked], locate(model))

        self._model = model

    def to_record_value(self, value: Any) -> list:
        return list(value)

    def to_internal_value(self, value: list) -> list:
        return list(value)

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, list):
            raise ValueError(f"LookupField '{self.field_name}' value ({value}) must be a 'list'")

    def __get__(self, *args, **kwargs) -> Optional[list]:
        return super().__get__(*args, **kwargs)


class LinkField(Field, Generic[T_Linked]):
    """Airtable Link field. Uses ``List[Model]`` to store value"""

    def __init__(
        self, field_name: str, model: Union[str, Type[T_Linked]], lazy=True
    ) -> None:
        """

        Args:
            field_name: Name of Airtable Column
            model: Model of Linked Type. Must be subtype of :class:`Model`
            lazy: Use `True` to load linked model when looking up attribute. `False`
                will create empty object with only `id` but will not fetch fields.

        Usage:
            >>> TODO
        """

        if isinstance(model, str):
            raise NotImplementedError("path import not implemented")
            # https://github.com/FactoryBoy/factory_boy/blob/37f962720814dff42d7a6a848ccfd200fc7f5ae2/factory/declarations.py#L339
            # model = cast(Type[T_Linked], locate(model))

        assert hasattr(model, "get_table"), "model be subclassed from Model"
        self._model = model
        self._lazy = lazy
        super().__init__(field_name)

    def __get__(self, *args, **kwargs) -> List[T_Linked]:
        return super().__get__(*args, **kwargs)

    def valid_or_raise(self, value) -> None:
        if not hasattr(value, "__iter__"):
            raise TypeError("LinkField value must be iterable")
        for model_instance in value:
            if not isinstance(model_instance, self._model):
                raise ValueError("must be model intance")

    def to_internal_value(self, value: Any) -> List[T_Linked]:
        # If Lazy, create empty from model class and set id
        # If not Lazy, fetch record from pyairtable and create new model instance
        should_fetch = not self._lazy
        linked_models = [
            self._model._linked_cache.get(id_)
            or self._model.from_id(id_, fetch=should_fetch)
            for id_ in value
        ]
        # self._model._linked_cache.update({m.id: m for m in linked_models})
        return linked_models

    def to_record_value(self, value: Any) -> List[str]:
        return [v.id for v in value]


"""
- [ ] autoNumber
- [ ] barcode
- [ ] button
- [x] checkbox
- [ ] count
- [ ] createdBy
- [ ] createdTime
- [ ] currency
- [x] date
- [x] dateTime
- [ ] duration
- [x] email
- [ ] externalSyncSource
- [ ] formula
- [ ] lastModifiedBy
- [ ] lastModifiedTime
- [ ] multilineText
- [ ] multipleAttachments
- [ ] multipleCollaborators
- [x] multipleLookupValues
- [ ] multipleRecordLinks
- [ ] multipleSelects
- [x] number
- [ ] percent
- [ ] phoneNumber
- [ ] rating
- [ ] richText
- [ ] rollup
- [ ] singleCollaborator
- [x] singleLineText
- [ ] singleSelect
- [ ] url
"""
