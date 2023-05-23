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
offers a special behaviour that can fetch linked records, so that you can
traverse between related records.

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
"""
import abc
from datetime import date, datetime, timedelta
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from typing_extensions import Self as SelfType
from typing_extensions import TypeAlias

from pyairtable import utils
from pyairtable.api.types import (
    AttachmentDict,
    BarcodeDict,
    ButtonDict,
    CollaboratorDict,
    RecordId,
)

if TYPE_CHECKING:
    from pyairtable.orm import Model  # noqa


_ClassInfo: TypeAlias = Union[type, Tuple["_ClassInfo", ...]]
T = TypeVar("T")
T_Linked = TypeVar("T_Linked", bound="Model")
T_API = TypeVar("T_API")  # type used to exchange values w/ Airtable API
T_ORM = TypeVar("T_ORM")  # type used to store values internally


class Field(Generic[T_API, T_ORM], metaclass=abc.ABCMeta):
    """
    A generic class for an Airtable field descriptor that will be
    included in an ORM model.

    Type-checked subclasses should provide two type parameters,
    ``T_API`` and ``T_ORM``, which indicate the type returned
    by the API and the type used to store values internally.

    Subclasses should also define ``valid_types`` as a type
    or tuple of types, which will be used to validate the type
    of field values being set via this descriptor.
    """

    #: Types that are allowed to be passed to this field.
    valid_types: ClassVar[_ClassInfo] = ()

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

    def __set_name__(self, owner: Any, name: str) -> None:
        self._model = owner
        self._attribute_name = name

    # __get__ and __set__ are called when accessing an instance of Field on an object.
    # Model.field should return the Field instance itself, whereas
    # obj.field should return the field's value from the Model instance obj.

    # Model.field will call __get__(instance=None, owner=Model)
    @overload
    def __get__(self, instance: None, owner: Type[Any]) -> SelfType:
        ...

    # obj.field will call __get__(instance=obj, owner=Model)
    @overload
    def __get__(self, instance: "Model", owner: Type[Any]) -> Optional[T_ORM]:
        ...

    def __get__(
        self, instance: Optional["Model"], owner: Type[Any]
    ) -> Union[SelfType, Optional[T_ORM]]:
        # allow calling Model.field to get the field object instead of a value
        if not instance:
            return self
        return self.get_value(instance)

    def get_value(self, instance: "Model") -> Optional[T_ORM]:
        """
        Given an instance of the Model, retrieve the field value from it.
        Easier for subclasses to override than __get__.
        """
        try:
            return cast(T_ORM, instance._fields[self.field_name])
        except (KeyError, AttributeError):
            return self._missing_value()

    def __set__(self, instance: "Model", value: Optional[T_ORM]) -> None:
        self._raise_if_readonly()
        if not hasattr(instance, "_fields"):
            instance._fields = {}
        if self.validate_type:
            self.valid_or_raise(value)
        instance._fields[self.field_name] = value

    def __delete__(self, instance: "Model") -> None:
        raise AttributeError(
            f"cannot delete {self._model.__name__}.{self._attribute_name}"
        )

    def _missing_value(self) -> Optional[T_ORM]:
        return None

    def to_record_value(self, value: Any) -> Any:
        return value

    def to_internal_value(self, value: Any) -> Any:
        return value

    def valid_or_raise(self, value: Any) -> None:
        if self.valid_types and not isinstance(value, self.valid_types):
            raise TypeError(
                f"{self.__class__.__name__} value must be {self.valid_types}; got {type(value)}"
            )

    def _raise_if_readonly(self) -> None:
        if self.readonly:
            raise AttributeError(
                f"{self._model.__name__}.{self._attribute_name} is read-only"
            )

    def __repr__(self) -> str:
        return "<{} field_name='{}'>".format(self.__class__.__name__, self.field_name)


#: A generic Field whose internal and API representations are the same type.
BasicField: TypeAlias = Field[T, T]


#: An alias for any type of Field.
AnyField: TypeAlias = BasicField[Any]


class TextField(BasicField[str]):
    """
    Used for all Airtable text fields. Accepts `str`.
    """

    valid_types = str

    def to_internal_value(self, value: Any) -> str:
        return str(value)


class _NumericField(Generic[T], BasicField[T]):
    """Base class for Number, Float, and Integer. Shares a common validation rule."""

    def valid_or_raise(self, value: Any) -> None:
        # Because `bool` is a subclass of `int`, we have to explicitly check for it here.
        if isinstance(value, bool):
            raise TypeError(
                f"{self.__class__.__name__} value must be {self.valid_types}; got {type(value)}"
            )
        return super().valid_or_raise(value)


class NumberField(_NumericField[Union[int, float]]):
    """
    Number field with unspecified precision. Accepts either `int` or `float`.
    """

    valid_types = (int, float)

    def to_internal_value(self, value: Any) -> Any:
        if not isinstance(value, (float, int)):
            raise TypeError(type(value))
        return value


# This cannot inherit from NumberField because valid_types would be more restrictive
# in the subclass than what is defined in the parent class.
class IntegerField(_NumericField[int]):
    """
    Number field with integer precision. Accepts only `int` values.
    """

    valid_types = int

    def to_internal_value(self, value: Any) -> int:
        return int(value)


# This cannot inherit from NumberField because valid_types would be more restrictive
# in the subclass than what is defined in the parent class.
class FloatField(_NumericField[float]):
    """
    Number field with decimal precision. Accepts only `float` values.
    """

    valid_types = float

    def to_internal_value(self, value: Any) -> float:
        return float(value)


class RatingField(IntegerField):
    """
    Accepts `int` values that are 1 or greater.
    """

    def valid_or_raise(self, value: int) -> None:
        super().valid_or_raise(value)
        if value < 1:
            raise ValueError("rating cannot be below 1")


class CheckboxField(BasicField[bool]):
    """
    Returns `False` instead of `None` if the field is empty on the Airtable base.
    """

    valid_types = bool

    def _missing_value(self) -> bool:
        return False

    def to_internal_value(self, value: Any) -> bool:
        return bool(value)


class DatetimeField(Field[str, datetime]):
    """
    DateTime field. Accepts only `datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`_ values.
    """

    valid_types = datetime

    def to_record_value(self, value: datetime) -> str:
        """Airtable expects ISO 8601 string datetime eg. "2014-09-05T12:34:56.000Z" """
        return utils.datetime_to_iso_str(value)

    def to_internal_value(self, value: str) -> datetime:
        """Airtable returns ISO 8601 string datetime eg. "2014-09-05T07:00:00.000Z" """
        return utils.datetime_from_iso_str(value)


class DateField(Field[str, date]):
    """
    Date field. Accepts only `date <https://docs.python.org/3/library/datetime.html#date-objects>`_ values.
    """

    valid_types = date

    def to_record_value(self, value: date) -> str:
        """Airtable expects ISO 8601 date string eg. "2014-09-05"""
        return utils.date_to_iso_str(value)

    def to_internal_value(self, value: str) -> date:
        """Airtable returns ISO 8601 date string eg. "2014-09-05"""
        return utils.date_from_iso_str(value)


class DurationField(Field[int, timedelta]):
    """
    Duration field. Accepts only `timedelta <https://docs.python.org/3/library/datetime.html#timedelta-objects>`_ values.
    Airtable's API returns this as a number of seconds.
    """

    valid_types = timedelta

    def to_record_value(self, value: timedelta) -> float:
        return value.total_seconds()

    def to_internal_value(self, value: Union[int, float]) -> timedelta:
        return timedelta(seconds=value)


class _DictField(Generic[T], BasicField[T]):
    """
    Generic field type that stores a single dict. Not for use via API;
    should be subclassed by concrete field types (below).
    """

    valid_types = dict


class ListField(Generic[T], Field[List[RecordId], List[T]]):
    """
    Generic type for a field that stores a list of values. Can be used
    to refer to a lookup field that might return more than one value.

    >>> from pyairtable.orm import fields as F
    >>> class MyTable(Model):
    ...     class Meta:
    ...         ...
    ...
    ...     lookup = F.ListField[str]("My Lookup", readonly=True)
    ...
    >>> rec = MyTable.first()
    >>> rec.lookup
    ["First value", "Second value", ...]
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

    def get_value(self, model: "Model") -> List[T]:
        value = super().get_value(model)
        if value is None:
            value = []
            setattr(model, self._attribute_name, value)
        return value

    def valid_or_raise(self, value: Any) -> None:
        super().valid_or_raise(value)
        if value is None:
            value = []
        if not isinstance(value, list):
            raise TypeError(type(value))
        if self.linked_model:
            for obj in value:
                if not isinstance(obj, self.linked_model):
                    raise TypeError(f"expected {self.linked_model}; got {type(obj)}")

    def to_internal_value(self, value: Optional[List[T]]) -> List[T]:
        if value is None:
            value = []
        return value


class LinkField(ListField[T_Linked]):
    """
    MultipleRecordLinks field. Accepts lists of Model instances.

    See :ref:`Link Fields`.
    """

    def __init__(
        self,
        field_name: str,
        model: Union[str, Type[T_Linked]],
        lazy: bool = True,
    ):
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
            cast(T_Linked, self.linked_model._linked_cache.get(id_))
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
    """
    Equivalent to ``IntegerField(readonly=True)``
    """

    readonly = True


class BarcodeField(_DictField[BarcodeDict]):
    """
    Accepts a `dict` that should conform to the format detailed in the
    `Barcode <https://airtable.com/developers/web/api/field-model#barcode>`_
    documentation.
    """


class ButtonField(_DictField[ButtonDict]):
    """
    Read-only field that returns a `dict`. For more information, read the
    `Button <https://airtable.com/developers/web/api/field-model#button>`_
    documentation.
    """

    readonly = True


class CollaboratorField(_DictField[CollaboratorDict]):
    """
    Accepts a `dict` that should conform to the format detailed in the
    `Collaborator <https://airtable.com/developers/web/api/field-model#collaborator>`_
    documentation.
    """


class CountField(IntegerField):
    """
    Equivalent to ``IntegerField(readonly=True)``
    """

    readonly = True


class CreatedByField(CollaboratorField):
    """
    Equivalent to ``CollaboratorField(readonly=True)``
    """

    readonly = True


class CreatedTimeField(DatetimeField):
    """
    Equivalent to ``DatetimeField(readonly=True)``
    """

    readonly = True


class CurrencyField(NumberField):
    """
    Equivalent to ``NumberField``
    """


class EmailField(TextField):
    """
    Equivalent to ``TextField``.
    """


class ExternalSyncSourceField(TextField):
    """
    Equivalent to ``TextField(readonly=True)``
    """

    readonly = True


class LastModifiedByField(CollaboratorField):
    """
    Equivalent to ``CollaboratorField(readonly=True)``
    """

    readonly = True


class LastModifiedTimeField(DatetimeField):
    """
    Equivalent to ``DatetimeField(readonly=True)``
    """

    readonly = True


# TODO: LookupField actually needs to support other types besides str.
class LookupField(ListField[str]):
    """
    Equivalent to ``ListField[str]``.
    """

    linked_model = str


class MultipleAttachmentsField(ListField[AttachmentDict]):
    """
    Accepts a list of dicts that should conform to the format detailed in the
    `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`_
    documentation.
    """

    linked_model = cast(Type[AttachmentDict], dict)


class MultipleCollaboratorsField(ListField[CollaboratorDict]):
    """
    Accepts a list of dicts that should conform to the format detailed in the
    `Multiple Collaborators <https://airtable.com/developers/web/api/field-model#multicollaborator>`_
    documentation.
    """

    linked_model = cast(Type[CollaboratorDict], dict)


class MultipleSelectField(ListField[str]):
    """
    Accepts a list of ``str``.
    """

    linked_model = str


class PercentField(NumberField):
    """
    Equivalent to ``NumberField``
    """


class PhoneNumberField(TextField):
    """
    Equivalent to ``TextField``
    """


class RichTextField(TextField):
    """
    Equivalent to ``TextField``
    """


class SelectField(TextField):
    """
    Equivalent to ``TextField``
    """


class UrlField(TextField):
    """
    Equivalent to ``TextField``
    """


ALL_FIELDS = {
    field_class
    for name, field_class in vars().items()
    if isinstance(field_class, type)
    and issubclass(field_class, Field)
    and not name.startswith("_")
}
"""
Set of all Field subclasses exposed by the library.

:meta hide-value:
"""


READONLY_FIELDS = {cls for cls in ALL_FIELDS if cls.readonly}
"""
Set of all read-only Field subclasses exposed by the library.

:meta hide-value:
"""


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
"""
Mapping of Airtable field type names to their ORM classes.
See https://airtable.com/developers/web/api/field-model

The data type of "formula" and "rollup" fields will depend
on the underlying fields they reference, so it is not practical
for the ORM to know or detect those fields' types. These two
field type names are mapped to the constant ``NotImplemented``.

If you need to refer to a formula or rollup field in the ORM,
you need to know what type of value you expect it to contain.
You can then declare that as a read-only field:

.. code-block:: python

    from pyairtable.orm import fields as F

    class MyTable(Model):
        class Meta:
            ...

        formula_field = F.TextField("My Formula", readonly=True)
        rollup_field = F.IntegerField("Row Count", readonly=True)

:meta hide-value:
"""
