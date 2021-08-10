"""
Field classes are used to define the the data type of your Airtable columns.

Internally these are implemented as descritors, so they can access and set values
seamleslly.

Descriptors are also annotated so you can use them with mypy.

>>> contact.to_record()
{
    "id": recS6qSLw0OCA6Xul",
    "createdTime": "2021-07-14T06:42:37.000Z",
    "fields": {
        "First Name": "George",
        "Age": 20,
    }
}

Link Fields
-----------

In addition to standard data type fields, the :class:`LinkField` class
offers a special behaviour that can fetch related records.

In other words, you can transverse related records through their ``Link Fields``:

>>> contact.partner.first_name

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

if TYPE_CHECKING:
    from pyairtable.orm import Model  # noqa

T_Linked = TypeVar("T_Linked", bound="Model")


class Field(metaclass=abc.ABCMeta):
    def __init__(self, field_name, validate_type=True) -> None:
        self.field_name = field_name
        self.validate_type = True

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

    # @abc.abstractmethod
    def to_record_value(self, value: Any) -> Any:
        return value

    # @abc.abstractmethod
    def to_internal_value(self, value: Any) -> Any:
        return value

    # @abc.abstractmethod
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
        return value.isoformat(timespec="milliseconds") + "Z"

    def to_internal_value(self, value: str) -> datetime:
        """Airtable returns ISO 8601 string datetime eg. "2014-09-05T07:00:00.000Z" """
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, datetime):
            raise ValueError("DatetimeField value must be 'datetime'")

    def __get__(self, *args, **kwargs) -> Optional[datetime]:
        return super().__get__(*args, **kwargs)


class DateField(Field):
    """Airtable Date field. Uses ``Date`` to store value"""

    def to_record_value(self, value: date) -> str:
        """Airtable expects ISO 8601 date string eg. "2014-09-05"""
        return value.strftime("%Y-%m-%d")

    def to_internal_value(self, value: str) -> date:
        """Airtable returns ISO 8601 date string eg. "2014-09-05"""
        return datetime.strptime(value, "%Y-%m-%d").date()

    def valid_or_raise(self, value) -> None:
        if not isinstance(value, date):
            raise ValueError("DateField value must be 'date'")

    def __get__(self, *args, **kwargs) -> Optional[datetime]:
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
        return [self._model.from_id(id_, fetch=should_fetch) for id_ in value]

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
- [ ] multipleLookupValues
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
