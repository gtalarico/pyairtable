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
from datetime import date, datetime, timedelta
from types import GeneratorType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
)

from pyairtable import utils

if TYPE_CHECKING:
    from builtins import _ClassInfo

    from pyairtable.orm import Model  # noqa


T = TypeVar("T")
T_Linked = TypeVar("T_Linked", bound="Model")


class Field(metaclass=abc.ABCMeta):
    #: Types that are allowed to be passed to this field.
    valid_types: ClassVar["_ClassInfo"] = ()

    #: The value we'll use when a field value is not present in the record.
    value_if_missing: ClassVar[Any] = None

    #: Whether to allow modification of the value in this field.
    readonly: bool = False

    def __init__(
        self,
        field_name: str,
        validate_type: bool = True,
        readonly: Optional[bool] = None,
    ) -> None:
        """
        Args:
            field_name: The name of the field in Airtable.

        Keyword Args:
            validate_type: Whether to raise a TypeError if anything attempts to write
                an object of an unsupported type as a field value. If ``False``, you
                may encounter unpredictable behavior from the Airtable API.
            readonly: If ``True``, any attempt to write a value to this field will
                raise an ``AttributeError``. Each field implements appropriate default
                values, but you may find it useful to mark fields as readonly if you
                know that the access token your code uses does not have permission
                to modify specific fields.
        """
        self.field_name = field_name
        self.validate_type = validate_type

        # Each class will define its own default, but implementers can override it.
        # Overriding this to be `readonly=False` is probably always wrong, though.
        if readonly is not None:
            self.readonly = readonly

    def __set_name__(self, owner, name) -> None:
        self._model = owner
        self._attribute_name = name

    def __get__(self, instance, owner):
        # allow calling Model.field to get the field object instead of a value
        if not instance:
            return self

        field_name = self.field_name
        try:
            # Field Field is not yet in dict, return None
            return instance._fields[field_name]
        except (KeyError, AttributeError):
            return self.value_if_missing

    def __set__(self, instance, value):
        self._raise_if_readonly()
        if not hasattr(instance, "_fields"):
            instance._fields = {}
        if self.validate_type:
            self.valid_or_raise(value)
        instance._fields[self.field_name] = value

    def __delete__(self, instance):
        raise AttributeError(
            f"cannot delete {self._model.__name__}.{self._attribute_name}"
        )

    def to_record_value(self, value: Any) -> Any:
        return value

    def to_internal_value(self, value: Any) -> Any:
        return value

    def valid_or_raise(self, value) -> None:
        if self.valid_types and not isinstance(value, self.valid_types):
            raise TypeError(
                f"{self.__class__.__name__} value must be {self.valid_types}; got {type(value)}"
            )

    def _raise_if_readonly(self) -> None:
        if self.readonly:
            raise AttributeError(
                f"{self._model.__name__}.{self._attribute_name} is read-only"
            )

    def __repr__(self):
        return "<{} field_name='{}'>".format(self.__class__.__name__, self.field_name)


class TextField(Field):
    """Airtable Single Text or Multiline Text Fields. Uses ``str`` to store value"""

    valid_types = str

    def to_internal_value(self, value: Any) -> str:
        return str(value)

    def __get__(self, *args, **kwargs) -> Optional[str]:
        return super().__get__(*args, **kwargs)


class EmailField(TextField):
    """Airtable Email field. Uses ``str`` to store value"""


class _NumericField(Field):
    """Base class for Number, Float, and Integer. Shares a common validation rule."""

    def valid_or_raise(self, value) -> None:
        # Because `bool` is a subclass of `int`, we have to explicitly check for it here.
        if isinstance(value, bool):
            raise TypeError(
                f"{self.__class__.__name__} value must be {self.valid_types}; got {type(value)}"
            )
        return super().valid_or_raise(value)


class NumberField(_NumericField):
    """Airtable Number field with unspecified precision. Uses ``int`` or ``float`` to store value"""

    valid_types = (int, float)

    def to_internal_value(self, value: Any) -> Any:
        if not isinstance(value, (float, int)):
            raise TypeError(type(value))
        return value

    def __get__(self, *args, **kwargs) -> Optional[Union[int, float]]:
        return super().__get__(*args, **kwargs)


# This cannot inherit from NumberField because valid_types would be more restrictive
# in the subclass than what is defined in the parent class.
class IntegerField(_NumericField):
    """Airtable Number field with Integer Precision. Uses ``int`` to store value"""

    valid_types = int

    def to_internal_value(self, value: Any) -> int:
        return int(value)

    def __get__(self, *args, **kwargs) -> Optional[int]:
        return super().__get__(*args, **kwargs)


# This cannot inherit from NumberField because valid_types would be more restrictive
# in the subclass than what is defined in the parent class.
class FloatField(_NumericField):
    """Airtable Number field with Decimal precision. Uses ``float`` to store value"""

    valid_types = float

    def to_internal_value(self, value: Any) -> float:
        return float(value)

    def __get__(self, *args, **kwargs) -> Optional[float]:
        return super().__get__(*args, **kwargs)


class RatingField(IntegerField):
    def valid_or_raise(self, value: int) -> None:
        super().valid_or_raise(value)
        if value < 1:
            raise ValueError("rating cannot be below 1")


class CheckboxField(Field):
    """Airtable Checkbox field. Uses ``bool`` to store value"""

    valid_types = bool
    value_if_missing = False

    def to_internal_value(self, value: Any) -> bool:
        return bool(value)

    def __get__(self, *args, **kwargs) -> Optional[bool]:
        return super().__get__(*args, **kwargs)


class DatetimeField(Field):
    """Airtable Datetime field. Uses ``datetime`` to store value"""

    valid_types = datetime

    def to_record_value(self, value: datetime) -> str:
        """Airtable expects ISO 8601 string datetime eg. "2014-09-05T12:34:56.000Z" """
        return utils.datetime_to_iso_str(value)

    def to_internal_value(self, value: str) -> datetime:
        """Airtable returns ISO 8601 string datetime eg. "2014-09-05T07:00:00.000Z" """
        return utils.datetime_from_iso_str(value)

    def __get__(self, *args, **kwargs) -> Optional[datetime]:
        return super().__get__(*args, **kwargs)


class DateField(Field):
    """Airtable Date field. Uses ``Date`` to store value"""

    valid_types = date

    def to_record_value(self, value: date) -> str:
        """Airtable expects ISO 8601 date string eg. "2014-09-05"""
        return utils.date_to_iso_str(value)

    def to_internal_value(self, value: str) -> date:
        """Airtable returns ISO 8601 date string eg. "2014-09-05"""
        return utils.date_from_iso_str(value)

    def __get__(self, *args, **kwargs) -> Optional[date]:
        return super().__get__(*args, **kwargs)


class DurationField(Field):
    """
    Airtable's ``Duration`` field type, which the API returns as number of seconds.
    Stored as ``datetime.timedelta`` internally.
    """

    valid_types = timedelta

    def to_record_value(self, value: timedelta) -> float:
        return value.total_seconds()

    def to_internal_value(self, value: Union[int, float]) -> timedelta:
        return timedelta(seconds=value)

    def __get__(self, *args, **kwargs) -> Optional[timedelta]:
        return super().__get__(*args, **kwargs)


class _DictField(Field):
    """
    Generic field type that stores a single dict. Not for use via API;
    should be subclassed by concrete field types (below).
    """

    valid_types = dict

    def __get__(self, *args, **kwargs) -> Optional[dict]:
        return super().__get__(*args, **kwargs)


class ListField(Field, Generic[T]):
    """
    Generic type for a field that stores a list of values.
    """

    valid_types = list
    linked_model: Optional[Type[T]] = None

    def __init__(
        self,
        field_name: str,
        model: Optional[Type[T]] = None,
        validate_type: bool = True,
        readonly: Optional[bool] = None,
    ):
        """
        Constructs a new field.

        Args:
            field_name: Name of the Airtable field.
            model: Type we expect to get from the API.
        """
        super().__init__(field_name, validate_type=validate_type, readonly=readonly)
        if model is not None:
            self.linked_model = model

    def __get__(self, instance, owner) -> List[T]:
        value = super().__get__(instance, owner)
        if value is None:
            value = []
            setattr(instance, self._attribute_name, value)
        return value

    def __set__(self, instance, value) -> None:
        if isinstance(value, (set, tuple, GeneratorType)):
            value = list(value)
        super().__set__(instance, value)

    def valid_or_raise(self, value) -> None:
        super().valid_or_raise(value)
        if self.linked_model:
            for obj in value:
                if not isinstance(obj, self.linked_model):
                    raise TypeError(f"expected {self.linked_model}; got {type(obj)}")

    def to_internal_value(self, value: Optional[List[T]]) -> List[T]:
        if value is None:
            value = []
        return value


class LinkField(ListField[T_Linked]):
    """Airtable Link field. Uses ``List[Model]`` to store value"""

    def __init__(self, field_name: str, model: Union[str, Type[T_Linked]], lazy=True):
        """
        Args:
            field_name: Name of Airtable Column
            model: Model of Linked Type. Must be subtype of :class:`Model`
            lazy: Use `True` to load linked model when looking up attribute. `False`
                will create empty object with only `id` but will not fetch fields.
        """
        if isinstance(model, str):
            raise NotImplementedError("path import not implemented")
            # https://github.com/FactoryBoy/factory_boy/blob/37f962720814dff42d7a6a848ccfd200fc7f5ae2/factory/declarations.py#L339
            # model = cast(Type[T_Linked], locate(model))

        if not hasattr(model, "get_table"):
            raise TypeError(f"{type(model)} does not appear to subclass orm.Model")

        self._lazy = lazy
        super().__init__(field_name, model=model)

    def to_internal_value(self, value: Any) -> List[T_Linked]:
        # If Lazy, create empty from model class and set id
        # If not Lazy, fetch record from pyairtable and create new model instance
        if not self.linked_model:
            raise RuntimeError(f"{self.__class__.__name__} must be declared with model")
        should_fetch = not self._lazy
        linked_models = [
            self.linked_model._linked_cache.get(id_)
            or self.linked_model.from_id(id_, fetch=should_fetch)
            for id_ in value
        ]
        self.linked_model._linked_cache.update({m.id: m for m in linked_models})
        return linked_models

    def to_record_value(self, value: Any) -> List[str]:
        return [v.id for v in value]


# Many of these are "passthrough" subclasses for now. E.g. there is no real
# difference between `field = TextField()` and `field = PhoneNumberField()`.
#
# But we might choose to add more type-specific functionality later, so
# we'll allow implementers to get as specific as they care to and they might
# get some extra functionality for free in the future.


class AutoNumberField(IntegerField):
    readonly = True


class BarcodeField(_DictField):
    pass


class ButtonField(_DictField):
    readonly = True


class CollaboratorField(_DictField):
    pass


class CountField(IntegerField):
    readonly = True


class CreatedByField(CollaboratorField):
    readonly = True


class CreatedTimeField(DatetimeField):
    readonly = True


class CurrencyField(NumberField):
    pass


class ExternalSyncSourceField(TextField):
    readonly = True


class LastModifiedByField(CollaboratorField):
    readonly = True


class LastModifiedTimeField(DatetimeField):
    readonly = True


# TODO: LookupField actually needs to support other types besides str.
class LookupField(ListField[str]):
    linked_model = str


class MultipleAttachmentsField(ListField[dict]):
    """
    Accepts a list of dicts that should conform to the format detailed in the
    `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`_
    documentation.
    """

    linked_model = dict


class MultipleCollaboratorsField(ListField[dict]):
    linked_model = dict


class MultipleSelectField(ListField[str]):
    linked_model = str


class PercentField(NumberField):
    pass


class PhoneNumberField(TextField):
    pass


class RichTextField(TextField):
    pass


class SelectField(TextField):
    pass


class UrlField(TextField):
    pass


#: Set of all Field subclasses available.
ALL_FIELDS = {
    field_class
    for name, field_class in vars().items()
    if isinstance(field_class, type)
    and issubclass(field_class, Field)
    and not name.startswith("_")
}


#: Set of all Field subclasses that do not allow writes.
READONLY_FIELDS = {cls for cls in ALL_FIELDS if cls.readonly}


#: Mapping of Airtable field type names to their ORM classes.
#: See https://airtable.com/developers/web/api/field-model
#:
#: The data type of "formula" and "rollup" fields will depend
#: on the underlying fields they reference, so it is not practical
#: for the ORM to know or detect those fields' types. These two
#: field type names are mapped to the constant ``NotImplemented``.
FIELD_TYPES_TO_CLASSES = {
    "autoNumber": AutoNumberField,
    "barcode": BarcodeField,
    "button": ButtonField,
    "checkbox": CheckboxField,
    "count": CountField,
    "createdBy": CreatedByField,
    "createdTime": CreatedTimeField,
    "currency": CurrencyField,
    "date": DateField,
    "dateTime": DatetimeField,
    "duration": DurationField,
    "email": EmailField,
    "externalSyncSource": ExternalSyncSourceField,
    "formula": NotImplemented,
    "lastModifiedBy": LastModifiedByField,
    "lastModifiedTime": LastModifiedTimeField,
    "lookup": LookupField,
    "multilineText": TextField,
    "multipleAttachments": MultipleAttachmentsField,
    "multipleCollaborators": MultipleCollaboratorsField,
    "multipleRecordLinks": LinkField,
    "multipleSelects": MultipleSelectField,
    "number": NumberField,
    "percent": PercentField,
    "phoneNumber": PhoneNumberField,
    "rating": RatingField,
    "richText": RichTextField,
    "rollup": NotImplemented,
    "singleCollaborator": CollaboratorField,
    "singleLineText": TextField,
    "singleSelect": SelectField,
    "url": UrlField,
}
