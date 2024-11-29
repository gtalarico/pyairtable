"""
Fields define how you'll interact with your data when using the :doc:`orm`.

Internally these are implemented as `descriptors <https://docs.python.org/3/howto/descriptor.html>`_,
which allows us to define methods and type annotations for getting and setting attribute values.

>>> from pyairtable.orm import Model, fields
>>> class Contact(Model):
...     class Meta:
...         ...
...     name = fields.TextField("Name")
...     is_registered = fields.CheckboxField("Registered")
...
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
"""

import abc
import importlib
from datetime import date, datetime, timedelta
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

from typing_extensions import Self as SelfType
from typing_extensions import TypeAlias

from pyairtable import formulas, utils
from pyairtable.api.types import (
    AITextDict,
    AttachmentDict,
    BarcodeDict,
    ButtonDict,
    CollaboratorDict,
    CollaboratorEmailDict,
    CreateAttachmentDict,
    RecordId,
)
from pyairtable.exceptions import (
    MissingValueError,
    MultipleValuesError,
    UnsavedRecordError,
)
from pyairtable.orm.lists import AttachmentsList, ChangeTrackingList

if TYPE_CHECKING:
    from pyairtable.orm import Model


_ClassInfo: TypeAlias = Union[type, Tuple["_ClassInfo", ...]]
T = TypeVar("T")
T_Linked = TypeVar("T_Linked", bound="Model")  # used by LinkField
T_API = TypeVar("T_API")  # type used to exchange values w/ Airtable API
T_ORM = TypeVar("T_ORM")  # type used to represent values internally
T_ORM_List = TypeVar("T_ORM_List")  # type used for lists of internal values
T_Missing = TypeVar("T_Missing")  # type returned when Airtable has no value


class Field(Generic[T_API, T_ORM, T_Missing], metaclass=abc.ABCMeta):
    """
    A generic class for an Airtable field descriptor that will be
    included in an ORM model.

    Type-checked subclasses should provide three type parameters:

        * ``T_API``, indicating the JSON-serializable type returned by the API
        * ``T_ORM``, indicating the type used to store values internally
        * ``T_Missing``, indicating the type of value returned if the field is empty

    Subclasses should also define ``valid_types`` as a type
    or tuple of types, which will be used to validate the type
    of field values being set via this descriptor.
    """

    #: Types that are allowed to be passed to this field.
    valid_types: ClassVar[_ClassInfo] = ()

    #: The value to return when the field is missing
    missing_value: ClassVar[Any] = None

    #: Whether to allow modification of the value in this field.
    readonly: bool = False

    # Contains a reference to the Model class (if possible)
    _model: Optional[Type["Model"]] = None

    # The name of the attribute on the Model class (if possible)
    _attribute_name: Optional[str] = None

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
        """
        Called when an instance of Field is created within a class.
        """
        self._model = owner
        self._attribute_name = name

    @property
    def _description(self) -> str:
        """
        Describes the field for the purpose of logging an error message.
        Handles an edge case where a field is created directly onto a class
        that already exists; in those cases, __set_name__ is not called.
        """
        if self._model and self._attribute_name:
            return f"{self._model.__name__}.{self._attribute_name}"
        return f"{self.field_name!r} field"

    # __get__ and __set__ are called when accessing an instance of Field on an object.
    # Model.field should return the Field instance itself, whereas
    # obj.field should return the field's value from the Model instance obj.

    # Model.field will call __get__(instance=None, owner=Model)
    @overload
    def __get__(self, instance: None, owner: Type[Any]) -> SelfType: ...

    # obj.field will call __get__(instance=obj, owner=Model)
    @overload
    def __get__(
        self, instance: "Model", owner: Type[Any]
    ) -> Union[T_ORM, T_Missing]: ...

    def __get__(
        self, instance: Optional["Model"], owner: Type[Any]
    ) -> Union[SelfType, T_ORM, T_Missing]:
        # allow calling Model.field to get the field object instead of a value
        if not instance:
            return self
        try:
            value = instance._fields[self.field_name]
        except (KeyError, AttributeError):
            return cast(T_Missing, self.missing_value)
        if value is None:
            return cast(T_Missing, self.missing_value)
        return cast(T_ORM, value)

    def __set__(self, instance: "Model", value: Optional[T_ORM]) -> None:
        self._raise_if_readonly()
        if self.validate_type and value is not None:
            self.valid_or_raise(value)
        if not hasattr(instance, "_fields"):
            instance._fields = {}
        instance._fields[self.field_name] = value
        if hasattr(instance, "_changed"):
            instance._changed[self.field_name] = True

    def __delete__(self, instance: "Model") -> None:
        raise AttributeError(f"cannot delete {self._description}")

    def to_record_value(self, value: Any) -> Any:
        """
        Calculate the value which should be persisted to the API.
        """
        return value

    def to_internal_value(self, value: Any) -> Any:
        """
        Convert a value from the API into the value's internal representation.
        """
        return value

    def valid_or_raise(self, value: Any) -> None:
        """
        Validate the type of the given value and raise TypeError if invalid.
        """
        if self.valid_types and not isinstance(value, self.valid_types):
            raise TypeError(
                f"{self.__class__.__name__} value must be {self.valid_types}; got {type(value)}"
            )

    def _raise_if_readonly(self) -> None:
        if self.readonly:
            raise AttributeError(f"{self._description} is read-only")

    def __repr__(self) -> str:
        args = [repr(self.field_name)]
        args += [f"{key}={val!r}" for (key, val) in self._repr_fields()]
        return self.__class__.__name__ + "(" + ", ".join(args) + ")"

    def _repr_fields(self) -> List[Tuple[str, Any]]:
        return [
            ("readonly", self.readonly),
            ("validate_type", self.validate_type),
        ]

    def eq(self, value: Any) -> "formulas.Comparison":
        """
        Build an :class:`~pyairtable.formulas.EQ` comparison using this field.
        """
        return formulas.EQ(self, value)

    def ne(self, value: Any) -> "formulas.Comparison":
        """
        Build an :class:`~pyairtable.formulas.NE` comparison using this field.
        """
        return formulas.NE(self, value)

    def gt(self, value: Any) -> "formulas.Comparison":
        """
        Build a :class:`~pyairtable.formulas.GT` comparison using this field.
        """
        return formulas.GT(self, value)

    def lt(self, value: Any) -> "formulas.Comparison":
        """
        Build an :class:`~pyairtable.formulas.LT` comparison using this field.
        """
        return formulas.LT(self, value)

    def gte(self, value: Any) -> "formulas.Comparison":
        """
        Build a :class:`~pyairtable.formulas.GTE` comparison using this field.
        """
        return formulas.GTE(self, value)

    def lte(self, value: Any) -> "formulas.Comparison":
        """
        Build an :class:`~pyairtable.formulas.LTE` comparison using this field.
        """
        return formulas.LTE(self, value)


class _FieldWithRequiredValue(Generic[T_API, T_ORM], Field[T_API, T_ORM, T_ORM]):
    """
    A mix-in for a Field class which indicates two things:

    1. It should never receive a null value from the Airtable API.
    2. It should never allow other code to set it as None (or the empty string).

    If either of those conditions occur, the field will raise an exception.
    """

    @overload
    def __get__(self, instance: None, owner: Type[Any]) -> SelfType: ...

    @overload
    def __get__(self, instance: "Model", owner: Type[Any]) -> T_ORM: ...

    def __get__(
        self, instance: Optional["Model"], owner: Type[Any]
    ) -> Union[SelfType, T_ORM]:
        value = super().__get__(instance, owner)
        if value is None or value == "":
            raise MissingValueError(f"{self._description} received an empty value")
        return value

    def __set__(self, instance: "Model", value: Optional[T_ORM]) -> None:
        if value in (None, ""):
            raise MissingValueError(f"{self._description} does not accept empty values")
        super().__set__(instance, value)


#: A generic Field with internal and API representations that are the same type.
_BasicField: TypeAlias = Field[T, T, None]
_BasicFieldWithMissingValue: TypeAlias = Field[T, T, T]
_BasicFieldWithRequiredValue: TypeAlias = _FieldWithRequiredValue[T, T]


#: An alias for any type of Field.
AnyField: TypeAlias = Field[Any, Any, Any]


class TextField(_BasicFieldWithMissingValue[str]):
    """
    Accepts ``str``.
    Returns ``""`` instead of ``None`` if the field is empty on the Airtable base.

    See `Single line text <https://airtable.com/developers/web/api/field-model#simpletext>`__
    and `Long text <https://airtable.com/developers/web/api/field-model#multilinetext>`__.
    """

    missing_value = ""
    valid_types = str


class _NumericField(Generic[T], _BasicField[T]):
    """
    Base class for Number, Float, and Integer. Shares a common validation rule.
    """

    def valid_or_raise(self, value: Any) -> None:
        # Because `bool` is a subclass of `int`, we have to explicitly check for it here.
        if isinstance(value, bool):
            raise TypeError(
                f"{self.__class__.__name__} value must be {self.valid_types}; got {type(value)}"
            )
        return super().valid_or_raise(value)


class NumberField(_NumericField[Union[int, float]]):
    """
    Number field with unspecified precision. Accepts either ``int`` or ``float``.

    See `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.
    """

    valid_types = (int, float)


# This cannot inherit from NumberField because valid_types would be more restrictive
# in the subclass than what is defined in the parent class.
class IntegerField(_NumericField[int]):
    """
    Number field with integer precision. Accepts only ``int`` values.

    See `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.
    """

    valid_types = int


# This cannot inherit from NumberField because valid_types would be more restrictive
# in the subclass than what is defined in the parent class.
class FloatField(_NumericField[float]):
    """
    Number field with decimal precision. Accepts only ``float`` values.

    See `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.
    """

    valid_types = float


class RatingField(IntegerField):
    """
    Accepts ``int`` values that are greater than zero.

    See `Rating <https://airtable.com/developers/web/api/field-model#rating>`__.
    """

    def valid_or_raise(self, value: int) -> None:
        super().valid_or_raise(value)
        if value < 1:
            raise ValueError("rating cannot be below 1")


class CheckboxField(_BasicFieldWithMissingValue[bool]):
    """
    Accepts ``bool``.
    Returns ``False`` instead of ``None`` if the field is empty on the Airtable base.

    See `Checkbox <https://airtable.com/developers/web/api/field-model#checkbox>`__.
    """

    missing_value = False
    valid_types = bool


class DatetimeField(Field[str, datetime, None]):
    """
    DateTime field. Accepts only `datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`_ values.

    See `Date and time <https://airtable.com/developers/web/api/field-model#dateandtime>`__.
    """

    valid_types = datetime

    def to_record_value(self, value: datetime) -> str:
        """
        Convert a ``datetime`` into an ISO 8601 string, e.g. "2014-09-05T12:34:56.000Z".
        """
        return utils.datetime_to_iso_str(value)

    def to_internal_value(self, value: str) -> datetime:
        """
        Convert an ISO 8601 string, e.g. "2014-09-05T07:00:00.000Z" into a ``datetime``.
        """
        return utils.datetime_from_iso_str(value)


class DateField(Field[str, date, None]):
    """
    Date field. Accepts only `date <https://docs.python.org/3/library/datetime.html#date-objects>`_ values.

    See `Date <https://airtable.com/developers/web/api/field-model#dateonly>`__.
    """

    valid_types = date

    def to_record_value(self, value: date) -> str:
        """
        Convert a ``date`` into an ISO 8601 string, e.g. "2014-09-05".
        """
        return utils.date_to_iso_str(value)

    def to_internal_value(self, value: str) -> date:
        """
        Convert an ISO 8601 string, e.g. "2014-09-05" into a ``date``.
        """
        return utils.date_from_iso_str(value)


class DurationField(Field[int, timedelta, None]):
    """
    Duration field. Accepts only `timedelta <https://docs.python.org/3/library/datetime.html#timedelta-objects>`_ values.

    See `Duration <https://airtable.com/developers/web/api/field-model#durationnumber>`__.
    Airtable's API returns this as a number of seconds.
    """

    valid_types = timedelta

    def to_record_value(self, value: timedelta) -> float:
        """
        Convert a ``timedelta`` into a number of seconds.
        """
        return value.total_seconds()

    def to_internal_value(self, value: Union[int, float]) -> timedelta:
        """
        Convert a number of seconds into a ``timedelta``.
        """
        return timedelta(seconds=value)


class _DictField(Generic[T], _BasicField[T]):
    """
    Generic field type that stores a single dict. Not for use via API;
    should be subclassed by concrete field types (below).
    """

    valid_types = dict


class _ListFieldBase(
    Generic[T_API, T_ORM, T_ORM_List],
    Field[List[T_API], List[T_ORM], T_ORM_List],
):
    """
    Generic type for a field that stores a list of values.
    Not for direct use; should be subclassed by concrete field types (below).

    Generic type parameters:
        * ``T_API``: The type of value returned by the Airtable API.
        * ``T_ORM``: The type of value stored internally.
        * ``T_ORM_List``: The type of list object that will be returned.
    """

    valid_types = list
    list_class: Type[T_ORM_List]
    contains_type: Optional[Type[T_ORM]]

    # List fields will always return a list, never ``None``, so we
    # have to overload the type annotations for __get__

    def __init_subclass__(cls, **kwargs: Any) -> None:
        cls.contains_type = kwargs.pop("contains_type", None)
        cls.list_class = kwargs.pop("list_class", ChangeTrackingList)

        if cls.contains_type and not isinstance(cls.contains_type, type):
            raise TypeError(f"contains_type= expected a type, got {cls.contains_type}")
        if not isinstance(cls.list_class, type):
            raise TypeError(f"list_class= expected a type, got {cls.list_class}")
        if not issubclass(cls.list_class, ChangeTrackingList):
            raise TypeError(
                f"list_class= expected Type[ChangeTrackingList], got {cls.list_class}"
            )

        return super().__init_subclass__(**kwargs)

    @overload
    def __get__(self, instance: None, owner: Type[Any]) -> SelfType: ...

    @overload
    def __get__(self, instance: "Model", owner: Type[Any]) -> T_ORM_List: ...

    def __get__(
        self, instance: Optional["Model"], owner: Type[Any]
    ) -> Union[SelfType, T_ORM_List]:
        if not instance:
            return self
        return self._get_list_value(instance)

    def _get_list_value(self, instance: "Model") -> T_ORM_List:
        value = instance._fields.get(self.field_name)
        # If Airtable returns no value, substitute an empty list.
        if value is None:
            value = []

        # We need to keep track of any mutations to this list, so we know
        # whether to write the field back to the API when the model is saved.
        if not isinstance(value, self.list_class):
            # These were already checked in __init_subclass__ but mypy doesn't know that.
            assert isinstance(self.list_class, type)
            assert issubclass(self.list_class, ChangeTrackingList)
            value = self.list_class(value, field=self, model=instance)

        # For implementers to be able to modify this list in place
        # and persist it later when they call .save(), we need to
        # set the list as the field's value.
        instance._fields[self.field_name] = value
        return cast(T_ORM_List, value)

    def valid_or_raise(self, value: Any) -> None:
        super().valid_or_raise(value)
        if self.contains_type:
            for obj in value:
                if not isinstance(obj, self.contains_type):
                    raise TypeError(f"expected {self.contains_type}; got {type(obj)}")


class _ListField(Generic[T], _ListFieldBase[T, T, ChangeTrackingList[T]]):
    """
    Generic type for a field that stores a list of values.
    Not for direct use; should be subclassed by concrete field types (below).
    """


class _LinkFieldOptions(Enum):
    LinkSelf = object()


#: Sentinel option for the `model=` param to :class:`~LinkField`
LinkSelf = _LinkFieldOptions.LinkSelf


class LinkField(
    Generic[T_Linked],
    _ListFieldBase[RecordId, T_Linked, ChangeTrackingList[T_Linked]],
):
    """
    Represents a MultipleRecordLinks field. Returns and accepts lists of Models.

    Can also be used with a lookup field that pulls from a MultipleRecordLinks field,
    provided the field is created with ``readonly=True``.

    See `Link to another record <https://airtable.com/developers/web/api/field-model#foreignkey>`__.
    """

    _linked_model: Union[str, Literal[_LinkFieldOptions.LinkSelf], Type[T_Linked]]
    _max_retrieve: Optional[int] = None

    def __init__(
        self,
        field_name: str,
        model: Union[str, Literal[_LinkFieldOptions.LinkSelf], Type[T_Linked]],
        validate_type: bool = True,
        readonly: Optional[bool] = None,
        lazy: bool = False,
    ):
        """
        Args:
            field_name: Name of the Airtable field.
            model:
                Model class representing the linked table. There are a few options:

                1. You can provide a ``str`` that is the fully qualified module and class name.
                   For example, ``"your.module.Model"`` will import ``Model`` from ``your.module``.
                2. You can provide a ``str`` that is *just* the class name, and it will be imported
                   from the same module as the model class.
                3. You can provide the sentinel value :data:`~LinkSelf`, and the link field
                   will point to the same model where the link field is created.

            validate_type: Whether to raise a TypeError if attempting to write
                an object of an unsupported type as a field value. If ``False``, you
                may encounter unpredictable behavior from the Airtable API.
            readonly: If ``True``, any attempt to write a value to this field will
                raise an ``AttributeError``. This will not, however, prevent any
                modification of the list object returned by this field.
            lazy: If ``True``, this field will return empty objects with only IDs;
                call :meth:`~pyairtable.orm.Model.fetch` to retrieve values.
        """
        from pyairtable.orm import Model

        if not (
            model is _LinkFieldOptions.LinkSelf
            or isinstance(model, str)
            or (isinstance(model, type) and issubclass(model, Model))
        ):
            raise TypeError(f"expected str, Model, or LinkSelf; got {type(model)}")

        super().__init__(field_name, validate_type=validate_type, readonly=readonly)
        self._linked_model = model
        self._lazy = lazy

    @property
    def linked_model(self) -> Type[T_Linked]:
        """
        Resolve a :class:`~pyairtable.orm.Model` class based on
        the ``model=`` constructor parameter to this field instance.
        """
        if isinstance(self._linked_model, str):
            modpath, _, clsname = self._linked_model.rpartition(".")
            if not modpath:
                if self._model is None:
                    raise RuntimeError(f"{self._description} not created on a Model")
                modpath = self._model.__module__
            mod = importlib.import_module(modpath)
            cls = getattr(mod, clsname)
            self._linked_model = cast(Type[T_Linked], cls)

        elif self._linked_model is _LinkFieldOptions.LinkSelf:
            if self._model is None:
                raise RuntimeError(f"{self._description} not created on a Model")
            self._linked_model = cast(Type[T_Linked], self._model)

        return self._linked_model

    def _repr_fields(self) -> List[Tuple[str, Any]]:
        return [
            ("model", self._linked_model),
            ("validate_type", self.validate_type),
            ("readonly", self.readonly),
            ("lazy", self._lazy),
        ]

    def populate(
        self,
        instance: "Model",
        *,
        lazy: Optional[bool] = None,
        memoize: Optional[bool] = None,
    ) -> None:
        """
        Populates the field's value for the given instance. This allows you to
        control how linked models are loaded, depending on your need, without
        having to decide at the time of field or model construction.

        Args:
            instance: An instance of this field's :class:`~pyairtable.orm.Model` class.
            lazy: |kwarg_orm_lazy|
            memoize: |kwarg_orm_memoize|

        Usage:

            .. code-block:: python

                from pyairtable.orm import Model, fields as F

                class Book(Model):
                    class Meta: ...

                class Author(Model):
                    class Meta: ...
                    books = F.LinkField("Books", Book)

                author = Author.from_id("reculZ6qSLw0OCA61")
                Author.books.populate(author, lazy=True, memoize=False)
        """
        if self._model and not isinstance(instance, self._model):
            raise RuntimeError(
                f"populate() got {type(instance)}; expected {self._model}"
            )
        lazy = lazy if lazy is not None else self._lazy
        if not (records := super()._get_list_value(instance)):
            return
        # If there are any values which are IDs rather than instances,
        # retrieve their values in bulk, and store them keyed by ID
        # so we can maintain the order we received from the API.
        new_records = {}
        if new_record_ids := [
            v for v in records[: self._max_retrieve] if isinstance(v, RecordId)
        ]:
            new_records = {
                record.id: record
                for record in self.linked_model.from_ids(
                    cast(List[RecordId], new_record_ids),
                    memoize=memoize,
                    fetch=(not lazy),
                )
            }
        # If the list contains record IDs, replace the contents with instances.
        # Other code may already have references to this specific list, so
        # we replace the existing list's values.
        records[: self._max_retrieve] = [
            new_records[cast(RecordId, value)] if isinstance(value, RecordId) else value
            for value in records[: self._max_retrieve]
        ]

    def _get_list_value(self, instance: "Model") -> ChangeTrackingList[T_Linked]:
        """
        Unlike most other field classes, LinkField does not store its internal
        representation (T_ORM) in instance._fields after Model.from_record().
        They will first be stored as a list of IDs.

        We defer creating Model objects until they're requested for the first
        time, so we can avoid infinite recursion during to_internal_value().
        """
        self.populate(instance)
        return super()._get_list_value(instance)

    def to_record_value(self, value: List[Union[str, T_Linked]]) -> List[str]:
        """
        Build the list of record IDs which should be persisted to the API.
        """
        # If the _fields value contains str, it means we loaded it from the API
        # but we never actually accessed the value (see _get_list_value).
        # When persisting this model back to the API, we can just write those IDs.
        if all(isinstance(v, str) for v in value):
            return cast(List[str], value)

        # Validate any items in our list which are not record IDs
        records = [v for v in value if not isinstance(v, str)]
        self.valid_or_raise(records)
        if not all(record.exists() for record in records):
            # We could *try* to recursively save models that don't have an ID yet,
            # but that requires us to second-guess the implementers' intentions.
            # Better to just raise an exception.
            raise UnsavedRecordError(f"{self._description} contains an unsaved record")

        return [v if isinstance(v, str) else v.id for v in value]

    def valid_or_raise(self, value: Any) -> None:
        super().valid_or_raise(value)
        for obj in value:
            if not isinstance(obj, self.linked_model):
                raise TypeError(f"expected {self.linked_model}; got {type(obj)}")


class SingleLinkField(Generic[T_Linked], Field[List[str], T_Linked, None]):
    """
    Represents a MultipleRecordLinks field which we assume will only ever contain one link.
    Returns and accepts a single instance of the linked model, which will be converted to/from
    a list of IDs when communicating with the Airtable API.

    See `Link to another record <https://airtable.com/developers/web/api/field-model#foreignkey>`__.

    .. warning::

        If Airtable returns multiple IDs for a SingleLinkField and you modify the field value,
        only the first ID will be saved to the API once you call ``.save()``. The other IDs will be lost.

    By default, a SingleLinkField will ignore the 2nd...Nth IDs if it receives multiple IDs from the API.
    This behavior can be overridden by passing ``raise_if_many=True`` to the constructor.

    .. code-block:: python

        from pyairtable.orm import Model, fields as F

        class Book(Model):
            class Meta: ...

            author = F.SingleLinkField("Author", Person)
            editor = F.SingleLinkField("Editor", Person, raise_if_many=True)

    Given the model configuration above and the data below,
    one field will silently return a single value,
    while the other field will throw an exception.

    .. code-block:: python

        >>> book = Book.from_record({
        ...     "id": "recZ6qSLw0OCA61ul",
        ...     "createdTime": ...,
        ...     "fields": {
        ...         "Author": ["reculZ6qSLw0OCA61", "rec61ulZ6qSLw0OCA"],
        ...         "Editor": ["recLw0OCA61ulZ6qS", "recOCA61ulZ6qSLw0"],
        ...     }
        ... })
        >>> book.author
        <Person id='reculZ6qSLw0OCA61'>
        >>> book.editor
        Traceback (most recent call last):
          ...
        MultipleValues: Book.editor got more than one linked record

    """

    @utils.docstring_from(
        LinkField.__init__,
        append="""
            raise_if_many: If ``True``, this field will raise a
                :class:`~pyairtable.orm.fields.MultipleValues` exception upon
                being accessed if the underlying field contains multiple values.
        """,
    )
    def __init__(
        self,
        field_name: str,
        model: Union[str, Literal[_LinkFieldOptions.LinkSelf], Type[T_Linked]],
        validate_type: bool = True,
        readonly: Optional[bool] = None,
        lazy: bool = False,
        raise_if_many: bool = False,
    ):
        super().__init__(field_name, validate_type=validate_type, readonly=readonly)
        self._raise_if_many = raise_if_many
        # composition is easier than inheritance in this case ¯\_(ツ)_/¯
        self._link_field = LinkField[T_Linked](
            field_name,
            model,
            validate_type=validate_type,
            readonly=readonly,
            lazy=lazy,
        )
        self._link_field._max_retrieve = 1

    def _repr_fields(self) -> List[Tuple[str, Any]]:
        return [
            ("model", self._link_field._linked_model),
            ("validate_type", self.validate_type),
            ("readonly", self.readonly),
            ("lazy", self._link_field._lazy),
            ("raise_if_many", self._raise_if_many),
        ]

    @overload
    def __get__(self, instance: None, owner: Type[Any]) -> SelfType: ...

    @overload
    def __get__(self, instance: "Model", owner: Type[Any]) -> Optional[T_Linked]: ...

    def __get__(
        self, instance: Optional["Model"], owner: Type[Any]
    ) -> Union[SelfType, Optional[T_Linked]]:
        if not instance:
            return self
        if self._raise_if_many and len(instance._fields.get(self.field_name) or []) > 1:
            raise MultipleValuesError(
                f"{self._description} got more than one linked record"
            )
        links = self._link_field.__get__(instance, owner)
        try:
            return links[0]
        except IndexError:
            return None

    def __set__(self, instance: "Model", value: Optional[T_Linked]) -> None:
        values = None if value is None else [value]
        self._link_field.__set__(instance, values)

    def __set_name__(self, owner: Any, name: str) -> None:
        super().__set_name__(owner, name)
        self._link_field.__set_name__(owner, name)

    def to_record_value(self, value: List[Union[str, T_Linked]]) -> List[str]:
        return self._link_field.to_record_value(value)

    @utils.docstring_from(LinkField.populate)
    def populate(
        self,
        instance: "Model",
        *,
        lazy: Optional[bool] = None,
        memoize: Optional[bool] = None,
    ) -> None:
        self._link_field.populate(instance, lazy=lazy, memoize=memoize)

    @property
    @utils.docstring_from(LinkField.linked_model)
    def linked_model(self) -> Type[T_Linked]:
        return self._link_field.linked_model


# Many of these are "passthrough" subclasses for now. E.g. there is no real
# difference between `field = TextField()` and `field = PhoneNumberField()`.
#
# But we might choose to add more type-specific functionality later, so
# we'll allow implementers to get as specific as they care to and they might
# get some extra functionality for free in the future.


class AITextField(_DictField[AITextDict]):
    """
    Read-only field that returns a `dict`. For more information, read the
    `AI Text <https://airtable.com/developers/web/api/field-model#aitext>`_
    documentation.
    """

    readonly = True


class AttachmentsField(
    _ListFieldBase[
        AttachmentDict,
        Union[AttachmentDict, CreateAttachmentDict],
        AttachmentsList,
    ],
    list_class=AttachmentsList,
    contains_type=dict,
):
    """
    Accepts a list of dicts in the format detailed in
    `Attachments <https://airtable.com/developers/web/api/field-model#multipleattachment>`_.
    """


class BarcodeField(_DictField[BarcodeDict]):
    """
    Accepts a `dict` that should conform to the format detailed in the
    `Barcode <https://airtable.com/developers/web/api/field-model#barcode>`_
    documentation.
    """


class CollaboratorField(_DictField[Union[CollaboratorDict, CollaboratorEmailDict]]):
    """
    Accepts a `dict` that should conform to the format detailed in the
    `Collaborator <https://airtable.com/developers/web/api/field-model#collaborator>`_
    documentation.
    """


class CountField(IntegerField):
    """
    Equivalent to :class:`IntegerField(readonly=True) <IntegerField>`.

    See `Count <https://airtable.com/developers/web/api/field-model#count>`__.
    """

    readonly = True


class CurrencyField(NumberField):
    """
    Equivalent to :class:`~NumberField`.

    See `Currency <https://airtable.com/developers/web/api/field-model#currencynumber>`__.
    """


class EmailField(TextField):
    """
    Equivalent to :class:`~TextField`.

    See `Email <https://airtable.com/developers/web/api/field-model#email>`__.
    """


class ExternalSyncSourceField(TextField):
    """
    Equivalent to :class:`TextField(readonly=True) <TextField>`.

    See `Sync source <https://airtable.com/developers/web/api/field-model#syncsource>`__.
    """

    readonly = True


class LastModifiedByField(_DictField[CollaboratorDict]):
    """
    See `Last modified by <https://airtable.com/developers/web/api/field-model#lastmodifiedby>`__.
    """

    readonly = True


class LastModifiedTimeField(DatetimeField):
    """
    Equivalent to :class:`DatetimeField(readonly=True) <DatetimeField>`.

    See `Last modified time <https://airtable.com/developers/web/api/field-model#lastmodifiedtime>`__.
    """

    readonly = True


class LookupField(Generic[T], _ListField[T]):
    """
    Generic field class for a lookup, which returns a list of values.

    pyAirtable does not inspect field configuration at runtime or during type checking.
    If you use mypy, you can declare which type(s) the lookup returns:

    >>> from pyairtable.orm import fields as F
    >>> class MyTable(Model):
    ...     Meta = fake_meta()
    ...     lookup = F.LookupField[str]("My Lookup")
    ...
    >>> rec = MyTable.first()
    >>> rec.lookup
    ["First value", "Second value", ...]

    See `Lookup <https://airtable.com/developers/web/api/field-model#lookup>`__.
    """

    readonly = True


class ManualSortField(TextField):
    """
    Field configuration for ``manualSort`` field type (not documented).
    """

    readonly = True


class MultipleCollaboratorsField(
    _ListField[Union[CollaboratorDict, CollaboratorEmailDict]], contains_type=dict
):
    """
    Accepts a list of dicts in the format detailed in
    `Multiple Collaborators <https://airtable.com/developers/web/api/field-model#multicollaborator>`_.
    """


class MultipleSelectField(_ListField[str], contains_type=str):
    """
    Accepts a list of ``str``.

    See `Multiple select <https://airtable.com/developers/web/api/field-model#multiselect>`__.
    """


class PercentField(NumberField):
    """
    Equivalent to :class:`~NumberField`.

    See `Percent <https://airtable.com/developers/web/api/field-model#percentnumber>`__.
    """


class PhoneNumberField(TextField):
    """
    Equivalent to :class:`~TextField`.

    See `Phone <https://airtable.com/developers/web/api/field-model#phone>`__.
    """


class RichTextField(TextField):
    """
    Equivalent to :class:`~TextField`.

    See `Rich text <https://airtable.com/developers/web/api/field-model#rich-text>`__.
    """


class SelectField(Field[str, str, None]):
    """
    Represents a single select dropdown field. This will return ``None`` if no value is set,
    and will only return ``""`` if an empty dropdown option is available and selected.

    See `Single select <https://airtable.com/developers/web/api/field-model#select>`__.
    """

    valid_types = str


class UrlField(TextField):
    """
    Equivalent to :class:`~TextField`.

    See `Url <https://airtable.com/developers/web/api/field-model#urltext>`__.
    """


# Auto-generate Required*Field classes for anything above this line
# fmt: off
r"""[[[cog]]]
import re
from collections import namedtuple

with open(cog.inFile) as fp:
    src = "".join(fp.readlines()[:cog.firstLineNum])

Match = namedtuple('Match', 'cls generic bases annotation cls_kwargs doc readonly')
expr = (
    r'(?m)'
    r'^class ([A-Z]\w+Field)'
        r'\('
            # This particular regex will not pick up Field subclasses that have
            # multiple inheritance, which excludes anything using _NotNullField.
            r'(?:(Generic\[.+?\]), )?'
            r'([_A-Z][_A-Za-z]+)(?:\[(.+?)\])?'
            r'((?:, [a-z_]+=.+)+)?'
        r'\):\n'
    r'    \"\"\"\n    ((?:.|\n)+?)    \"\"\"(?:\n|    (?!readonly =).*)*'
    r'(    readonly = True)?'
)
classes = {
    match.cls: match
    for group in re.findall(expr, src)
    if (match := Match(*group))
}

for cls, match in sorted(classes.items()):
    if cls in {
        # checkbox values are either `True` or missing
        "CheckboxField",

        # null value will be converted to an empty list
        "AttachmentsField",
        "LinkField",
        "LookupField",
        "MultipleCollaboratorsField",
        "MultipleSelectField",

        # unsupported
        "SingleLinkField",

        # illogical
        "LastModifiedByField",
        "LastModifiedTimeField",
        "ExternalSyncSourceField",
        "ManualSortField",
    }:
        continue

    # skip if we've already included Required
    if cls.startswith("Required") or "Required" in match.bases:
        continue

    base, typn = match.cls, match.annotation
    typn_bases = match.bases
    while not typn:
        typn = classes[typn_bases].annotation
        typn_bases = classes[typn_bases].bases

    if typn.endswith(", None"):
        typn = typn[:-len(", None")]

    mixin = ("_" if re.match(r"^[A-Za-z_.]+(\[\w+(, \w+)*\])?,", typn) else "_Basic") + "FieldWithRequiredValue"
    base = base if not match.generic else f"{base}, {match.generic}"
    cog.outl(f"\n\nclass Required{cls}({base}, {mixin}[{typn}]):")
    cog.outl('    \"\"\"')
    cog.outl('    ' + match.doc)
    cog.out( '    If the Airtable API returns ``null``, ')
    if not match.readonly:
        cog.out('or if a caller sets this field to ``None``,\n    ')
    cog.outl('this field raises :class:`~pyairtable.orm.fields.MissingValue`.')
    cog.outl('    \"\"\"')

cog.outl('\n')
[[[out]]]"""


class RequiredAITextField(AITextField, _BasicFieldWithRequiredValue[AITextDict]):
    """
    Read-only field that returns a `dict`. For more information, read the
    `AI Text <https://airtable.com/developers/web/api/field-model#aitext>`_
    documentation.

    If the Airtable API returns ``null``, this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredBarcodeField(BarcodeField, _BasicFieldWithRequiredValue[BarcodeDict]):
    """
    Accepts a `dict` that should conform to the format detailed in the
    `Barcode <https://airtable.com/developers/web/api/field-model#barcode>`_
    documentation.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredCollaboratorField(CollaboratorField, _BasicFieldWithRequiredValue[Union[CollaboratorDict, CollaboratorEmailDict]]):
    """
    Accepts a `dict` that should conform to the format detailed in the
    `Collaborator <https://airtable.com/developers/web/api/field-model#collaborator>`_
    documentation.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredCountField(CountField, _BasicFieldWithRequiredValue[int]):
    """
    Equivalent to :class:`IntegerField(readonly=True) <IntegerField>`.

    See `Count <https://airtable.com/developers/web/api/field-model#count>`__.

    If the Airtable API returns ``null``, this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredCurrencyField(CurrencyField, _BasicFieldWithRequiredValue[Union[int, float]]):
    """
    Equivalent to :class:`~NumberField`.

    See `Currency <https://airtable.com/developers/web/api/field-model#currencynumber>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredDateField(DateField, _FieldWithRequiredValue[str, date]):
    """
    Date field. Accepts only `date <https://docs.python.org/3/library/datetime.html#date-objects>`_ values.

    See `Date <https://airtable.com/developers/web/api/field-model#dateonly>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredDatetimeField(DatetimeField, _FieldWithRequiredValue[str, datetime]):
    """
    DateTime field. Accepts only `datetime <https://docs.python.org/3/library/datetime.html#datetime-objects>`_ values.

    See `Date and time <https://airtable.com/developers/web/api/field-model#dateandtime>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredDurationField(DurationField, _FieldWithRequiredValue[int, timedelta]):
    """
    Duration field. Accepts only `timedelta <https://docs.python.org/3/library/datetime.html#timedelta-objects>`_ values.

    See `Duration <https://airtable.com/developers/web/api/field-model#durationnumber>`__.
    Airtable's API returns this as a number of seconds.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredEmailField(EmailField, _BasicFieldWithRequiredValue[str]):
    """
    Equivalent to :class:`~TextField`.

    See `Email <https://airtable.com/developers/web/api/field-model#email>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredFloatField(FloatField, _BasicFieldWithRequiredValue[float]):
    """
    Number field with decimal precision. Accepts only ``float`` values.

    See `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredIntegerField(IntegerField, _BasicFieldWithRequiredValue[int]):
    """
    Number field with integer precision. Accepts only ``int`` values.

    See `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredNumberField(NumberField, _BasicFieldWithRequiredValue[Union[int, float]]):
    """
    Number field with unspecified precision. Accepts either ``int`` or ``float``.

    See `Number <https://airtable.com/developers/web/api/field-model#decimalorintegernumber>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredPercentField(PercentField, _BasicFieldWithRequiredValue[Union[int, float]]):
    """
    Equivalent to :class:`~NumberField`.

    See `Percent <https://airtable.com/developers/web/api/field-model#percentnumber>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredPhoneNumberField(PhoneNumberField, _BasicFieldWithRequiredValue[str]):
    """
    Equivalent to :class:`~TextField`.

    See `Phone <https://airtable.com/developers/web/api/field-model#phone>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredRatingField(RatingField, _BasicFieldWithRequiredValue[int]):
    """
    Accepts ``int`` values that are greater than zero.

    See `Rating <https://airtable.com/developers/web/api/field-model#rating>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredRichTextField(RichTextField, _BasicFieldWithRequiredValue[str]):
    """
    Equivalent to :class:`~TextField`.

    See `Rich text <https://airtable.com/developers/web/api/field-model#rich-text>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredSelectField(SelectField, _FieldWithRequiredValue[str, str]):
    """
    Represents a single select dropdown field. This will return ``None`` if no value is set,
    and will only return ``""`` if an empty dropdown option is available and selected.

    See `Single select <https://airtable.com/developers/web/api/field-model#select>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredTextField(TextField, _BasicFieldWithRequiredValue[str]):
    """
    Accepts ``str``.
    Returns ``""`` instead of ``None`` if the field is empty on the Airtable base.

    See `Single line text <https://airtable.com/developers/web/api/field-model#simpletext>`__
    and `Long text <https://airtable.com/developers/web/api/field-model#multilinetext>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


class RequiredUrlField(UrlField, _BasicFieldWithRequiredValue[str]):
    """
    Equivalent to :class:`~TextField`.

    See `Url <https://airtable.com/developers/web/api/field-model#urltext>`__.

    If the Airtable API returns ``null``, or if a caller sets this field to ``None``,
    this field raises :class:`~pyairtable.orm.fields.MissingValue`.
    """


# [[[end]]] (checksum: 5078434bb8fd65fa8f0be48de6915c2d)
# fmt: on


class AutoNumberField(RequiredIntegerField):
    """
    Equivalent to :class:`IntegerField(readonly=True) <IntegerField>`.

    See `Auto number <https://airtable.com/developers/web/api/field-model#autonumber>`__.

    If the Airtable API returns ``null``, this field will raise :class:`~pyairtable.orm.fields.MissingValue`.
    """

    readonly = True


class ButtonField(_DictField[ButtonDict], _BasicFieldWithRequiredValue[ButtonDict]):
    """
    Read-only field that returns a `dict`. For more information, read the
    `Button <https://airtable.com/developers/web/api/field-model#button>`_
    documentation.

    If the Airtable API returns ``null``, this field will raise :class:`~pyairtable.orm.fields.MissingValue`.
    """

    readonly = True


class CreatedByField(_BasicFieldWithRequiredValue[CollaboratorDict]):
    """
    See `Created by <https://airtable.com/developers/web/api/field-model#createdby>`__.

    If the Airtable API returns ``null``, this field will raise :class:`~pyairtable.orm.fields.MissingValue`.
    """

    readonly = True


class CreatedTimeField(RequiredDatetimeField):
    """
    Equivalent to :class:`DatetimeField(readonly=True) <DatetimeField>`.

    See `Created time <https://airtable.com/developers/web/api/field-model#createdtime>`__.

    If the Airtable API returns ``null``, this field will raise :class:`~pyairtable.orm.fields.MissingValue`.
    """

    readonly = True


#: Set of all Field subclasses exposed by the library.
#:
#: :meta hide-value:
ALL_FIELDS: Set[Type[AnyField]] = {
    field_class
    for name, field_class in vars().items()
    if isinstance(field_class, type)
    and issubclass(field_class, Field)
    and field_class is not Field
    and not name.startswith("_")
}


#: Set of all read-only Field subclasses exposed by the library.
#:
#: :meta hide-value:
READONLY_FIELDS: Set[Type[AnyField]] = {cls for cls in ALL_FIELDS if cls.readonly}


#: Mapping of Airtable field type names to their ORM classes.
#: See https://airtable.com/developers/web/api/field-model
#: and :ref:`Formula, Rollup, and Lookup Fields`.
#:
#: The data type of "formula" and "rollup" fields will depend
#: on the underlying fields they reference, so it is not practical
#: for the ORM to know or detect those fields' types. These two
#: field type names are mapped to the constant ``NotImplemented``.
#:
#: :meta hide-value:
FIELD_TYPES_TO_CLASSES: Dict[str, Type[AnyField]] = {
    "aiText": AITextField,
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
    "manualSort": ManualSortField,
    "multilineText": TextField,
    "multipleAttachments": AttachmentsField,
    "multipleCollaborators": MultipleCollaboratorsField,
    "multipleLookupValues": LookupField,
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


#: Mapping of field classes to the set of supported Airtable field types.
#:
#: :meta hide-value:
FIELD_CLASSES_TO_TYPES: Dict[Type[AnyField], Set[str]] = {
    cls: {key for (key, val) in FIELD_TYPES_TO_CLASSES.items() if val == cls}
    for cls in ALL_FIELDS
}


# Auto-generate __all__ to explicitly exclude any imported values
#
# [[[cog]]]
# import re
#
# with open(cog.inFile) as fp:
#     src = fp.read()
#
# classes = re.findall(r"^class ((?:[A-Z]\w+)?Field)\b", src, re.MULTILINE)
# constants = re.findall(r"^(?!T_)([A-Z][A-Z_]+)(?:: [^=]+)? = ", src, re.MULTILINE)
# aliases = re.findall(r"^(\w+): TypeAlias\b", src, re.MULTILINE)
# extras = ["LinkSelf"]
# names = constants + sorted(classes + aliases + extras)
#
# cog.outl("\n\n__all__ = [")
# for name in names:
#     if not name.startswith("_"):
#         cog.outl(f'    "{name}",')
# cog.outl("]")
# [[[out]]]


__all__ = [
    "ALL_FIELDS",
    "READONLY_FIELDS",
    "FIELD_TYPES_TO_CLASSES",
    "FIELD_CLASSES_TO_TYPES",
    "AITextField",
    "AnyField",
    "AttachmentsField",
    "AutoNumberField",
    "BarcodeField",
    "ButtonField",
    "CheckboxField",
    "CollaboratorField",
    "CountField",
    "CreatedByField",
    "CreatedTimeField",
    "CurrencyField",
    "DateField",
    "DatetimeField",
    "DurationField",
    "EmailField",
    "ExternalSyncSourceField",
    "Field",
    "FloatField",
    "IntegerField",
    "LastModifiedByField",
    "LastModifiedTimeField",
    "LinkField",
    "LinkSelf",
    "LookupField",
    "ManualSortField",
    "MultipleCollaboratorsField",
    "MultipleSelectField",
    "NumberField",
    "PercentField",
    "PhoneNumberField",
    "RatingField",
    "RequiredAITextField",
    "RequiredBarcodeField",
    "RequiredCollaboratorField",
    "RequiredCountField",
    "RequiredCurrencyField",
    "RequiredDateField",
    "RequiredDatetimeField",
    "RequiredDurationField",
    "RequiredEmailField",
    "RequiredFloatField",
    "RequiredIntegerField",
    "RequiredNumberField",
    "RequiredPercentField",
    "RequiredPhoneNumberField",
    "RequiredRatingField",
    "RequiredRichTextField",
    "RequiredSelectField",
    "RequiredTextField",
    "RequiredUrlField",
    "RichTextField",
    "SelectField",
    "SingleLinkField",
    "TextField",
    "UrlField",
]
# [[[end]]] (checksum: 87b0a100c9e30523d9aab8cc935c7960)
