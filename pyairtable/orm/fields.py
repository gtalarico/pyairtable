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


class Field:
    def __init__(self, field_name) -> None:
        self.field_name = field_name

    def __get__(self, instance, cls=None):
        # Raise if descriptor is called on class, where instance is None
        if not instance:
            raise ValueError("cannot access descriptors on class")

        field_name = self.field_name
        try:
            return instance._fields[field_name]
        except (KeyError, AttributeError):
            return None

    def __set__(self, instance, value):
        if not hasattr(instance, "_fields"):
            instance._fields = {}

        converted_value = self.to_internal_value(value)
        instance._fields[self.field_name] = converted_value

    @staticmethod
    def to_record_value(value: Any) -> Any:
        return value

    @staticmethod
    def to_internal_value(value: Any) -> Any:
        return value

    def __repr__(self):
        return "<{} field_name='{}'>".format(self.__class__.__name__, self.field_name)


class TextField(Field):
    """Airtable Single Text or Multiline Text Fields. Uses ``str`` to store value"""

    @staticmethod
    def to_internal_value(value: Any) -> str:
        return str(value)

    def __get__(self, *args, **kwargs) -> Optional[str]:
        return super().__get__(*args, **kwargs)


class IntegerField(Field):
    """Airtable Number field with Integer Precision. Uses ``int`` to store value"""

    @staticmethod
    def to_internal_value(value: Any) -> int:
        return int(value)

    def __get__(self, *args, **kwargs) -> Optional[int]:
        return super().__get__(*args, **kwargs)


class FloatField(Field):
    """Airtable Number field with Decimal precision. Uses ``float`` to store value"""

    @staticmethod
    def to_internal_value(value: Any) -> float:
        return float(value)

    def __get__(self, *args, **kwargs) -> Optional[float]:
        return super().__get__(*args, **kwargs)


class CheckboxField(Field):
    """Airtable Checkbox field. Uses ``bool`` to store value"""

    @staticmethod
    def to_internal_value(value: Any) -> bool:
        return bool(value)

    def __get__(self, *args, **kwargs) -> Optional[bool]:
        return super().__get__(*args, **kwargs)


class DatetimeField(Field):
    """Airtable Datetime field. Uses ``datetime`` to store value"""

    @staticmethod
    def to_record_value(value: datetime) -> str:
        """Airtable expects ISO 8601 string datetime eg. "2014-09-05T07:00:00.000Z" """
        return value.isoformat() + ".000Z"

    @staticmethod
    def to_internal_value(value: str) -> datetime:
        """Airtable returns ISO 8601 string datetime eg. "2014-09-05T07:00:00.000Z" """
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")

    def __get__(self, *args, **kwargs) -> Optional[datetime]:
        return super().__get__(*args, **kwargs)


class DateField(Field):
    """Airtable Date field. Uses ``Date`` to store value"""

    @staticmethod
    def to_record_value(value: date) -> str:
        """Airtable expects ISO 8601 date string eg. "2014-09-05"""
        return value.strftime("%Y-%m-%d")

    @staticmethod
    def to_internal_value(value: str) -> date:
        """Airtable returns ISO 8601 date string eg. "2014-09-05"""
        return datetime.strptime(value, "%Y-%m-%d").date()

    def __get__(self, *args, **kwargs) -> Optional[datetime]:
        return super().__get__(*args, **kwargs)


class EmailField(Field):
    """Airtable Email field. Uses ``str`` to store value"""

    def __get__(self, *args, **kwargs) -> Optional[str]:
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
        self._model = model
        self._lazy = lazy
        super().__init__(field_name)

    def __get__(self, instance: Any, cls=None) -> List[T_Linked]:
        """
        Gets value of :class:`LinkField` descriptor.

        Returns:
            List of Link Instances
        """
        if not instance:
            raise ValueError("cannot access descriptors on class")

        assert hasattr(instance, "get_table"), "instance be subclassed from Model"

        link_ids = instance._fields.get(self.field_name, [])

        instances = []
        for link_id in link_ids:

            # If cache, previous instance is used
            # This is needed to prevent loading a new instance on each attribute lookup
            cached_instance = instance._linked_cache.get(link_id)
            if cached_instance:
                instances.append(cached_instance)
                continue
            else:
                # If Lazy, create empty from model class and set id
                # If not Lazy, fetch record from pyairtable and create new model instance
                should_fetch = not self._lazy
                new_link_instance = self._model.from_id(link_id, fetch=should_fetch)

                # Cache instance
                instance._linked_cache[link_id] = new_link_instance
                instances.append(new_link_instance)

        return instances

    def __set__(self, instance, value: List[T_Linked]):
        """
        Sets value for LinkField descriptor.
        Value must be list of linked instances - eg:

        >>> contact.address = [address]
        """
        assert hasattr(value, "__iter__"), "LinkField value must be iterable"
        for model_instance in value:
            assert isinstance(model_instance, self._model), "must be model intance"
            # Store instance in cache and store id
            instance._linked_cache[model_instance.id] = model_instance
        ids = [i.id for i in value]
        super().__set__(instance, ids)

    @staticmethod
    def to_record_value(value: Any) -> Any:
        return value.id


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
