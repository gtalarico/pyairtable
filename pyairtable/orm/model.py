import dataclasses
import datetime
import warnings
from dataclasses import dataclass
from functools import cached_property
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Type,
    Union,
    cast,
)

from typing_extensions import Self as SelfType

from pyairtable.api import retrying
from pyairtable.api.api import Api, TimeoutTuple
from pyairtable.api.base import Base
from pyairtable.api.table import Table
from pyairtable.api.types import (
    FieldName,
    RecordDict,
    RecordId,
    UpdateRecordDict,
    WritableFields,
)
from pyairtable.formulas import EQ, OR, RECORD_ID
from pyairtable.models import Comment
from pyairtable.orm.fields import AnyField, Field
from pyairtable.utils import datetime_from_iso_str, datetime_to_iso_str

if TYPE_CHECKING:
    from builtins import _ClassInfo


class Model:
    """
    Supports creating ORM-style classes representing Airtable tables.
    For more details, see :ref:`orm`.

    A nested class or dict called ``Meta`` is required and can specify
    the following attributes:

        * ``api_key`` (required) - API key or personal access token.
        * ``base_id`` (required) - Base ID (not name).
        * ``table_name`` (required) - Table ID or name.
        * ``timeout`` - A tuple indicating a connect and read timeout. Defaults to no timeout.
        * ``typecast`` - |kwarg_typecast| Defaults to ``True``.
        * ``retry`` - An instance of `urllib3.util.Retry <https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry>`_.
          If ``None`` or ``False``, requests will not be retried.
          If ``True``, the default strategy will be applied
          (see :func:`~pyairtable.retry_strategy` for details).
        * ``use_field_ids`` - Whether fields will be defined by ID, rather than name. Defaults to ``False``.
        * ``memoize`` - Whether the model should reuse models it creates between requests.
          See :ref:`Memoizing linked records` for more information.

    For example, the following two are equivalent:

    .. code-block:: python

        from pyairtable.orm import Model, fields

        class Contact(Model):
            class Meta:
                base_id = "appaPqizdsNHDvlEm"
                table_name = "Contact"
                api_key = "keyapikey"
                timeout = (5, 5)
                typecast = True

            first_name = fields.TextField("First Name")
            age = fields.IntegerField("Age")

    .. code-block:: python

        from pyairtable.orm import Model, fields

        class Contact(Model):
            Meta = {
                "base_id": "appaPqizdsNHDvlEm",
                "table_name": "Contact",
                "api_key": "keyapikey",
                "timeout": (5, 5),
                "typecast": True,
            }
            first_name = fields.TextField("First Name")
            age = fields.IntegerField("Age")

    You can implement meta attributes as callables if certain values
    need to be dynamically provided or are unavailable at import time:

    .. code-block:: python

        from pyairtable.orm import Model, fields
        from your_app.config import get_secret

        class Contact(Model):
            class Meta:
                base_id = "appaPqizdsNHDvlEm"
                table_name = "Contact"

                @staticmethod
                def api_key():
                    return get_secret("AIRTABLE_API_KEY")

            first_name = fields.TextField("First Name")
            age = fields.IntegerField("Age")
    """

    #: The Airtable record ID for this instance. If empty, the instance
    #: has never been saved to the API.
    id: str = ""

    #: The time when the Airtable record was created. If empty, the instance
    #: has never been saved to (or fetched from) the API.
    created_time: Optional[datetime.datetime] = None

    #: A wrapper allowing type-annotated access to ORM configuration.
    meta: ClassVar["_Meta"]

    _deleted: bool = False
    _fetched: bool = False
    _fields: Dict[FieldName, Any]
    _changed: Dict[FieldName, bool]
    _memoized: ClassVar[Dict[RecordId, SelfType]]

    def __init_subclass__(cls, **kwargs: Any):
        cls.meta = _Meta(cls)
        cls._memoized = {}
        cls._validate_class()
        super().__init_subclass__(**kwargs)

    @classmethod
    def _validate_class(cls) -> None:
        # Verify required Meta attributes were set (but don't call any callables)
        assert cls.meta.get("api_key", required=True, call=False)
        assert cls.meta.get("base_id", required=True, call=False)
        assert cls.meta.get("table_name", required=True, call=False)

        model_attributes = [a for a in cls.__dict__.keys() if not a.startswith("__")]
        overridden = set(model_attributes).intersection(Model.__dict__.keys())
        if overridden:
            raise ValueError(
                "Class {cls} fields clash with existing method: {name}".format(
                    cls=cls.__name__, name=overridden
                )
            )

    @classmethod
    def _attribute_descriptor_map(cls) -> Dict[str, AnyField]:
        """
        Build a mapping of the model's attribute names to field descriptor instances.

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
        Build a mapping of the model's field names to field descriptor instances.

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

    def __init__(self, **fields: Any):
        """
        Construct a model instance with field values based on the given keyword args.

        >>> Contact(name="Alice", birthday=date(1980, 1, 1))
        <unsaved Contact>

        The keyword argument ``id=`` special-cased and sets the record ID, not a field value.

        >>> Contact(id="recWPqD9izdsNvlE", name="Bob")
        <Contact id='recWPqD9izdsNvlE'>
        """

        try:
            self.id = fields.pop("id")
        except KeyError:
            pass

        # Field values in internal (not API) representation
        self._fields = {}

        # Call __set__ on each field to set field values
        for key, value in fields.items():
            if key not in self._attribute_descriptor_map():
                raise AttributeError(key)
            setattr(self, key, value)

        # Only start tracking changes after the object is created
        self._changed = {}

    def __repr__(self) -> str:
        if not self.id:
            return f"<unsaved {self.__class__.__name__}>"
        return f"<{self.__class__.__name__} id={self.id!r}>"

    def exists(self) -> bool:
        """
        Whether the instance has been saved to Airtable already.
        """
        return bool(self.id)

    def save(self, *, force: bool = False) -> "SaveResult":
        """
        Save the model to the API.

        If the instance does not exist already, it will be created;
        otherwise, the existing record will be updated, using only the
        fields which have been modified since it was retrieved.

        Args:
            force: If ``True``, all fields will be saved, even if they have not changed.
        """
        if self._deleted:
            raise RuntimeError(f"{self.id} was deleted")

        field_values = self.to_record(only_writable=True)["fields"]

        if not self.id:
            record = self.meta.table.create(field_values, typecast=self.meta.typecast)
            self.id = record["id"]
            self.created_time = datetime_from_iso_str(record["createdTime"])
            self._changed.clear()
            return SaveResult(self.id, created=True, field_names=set(field_values))

        if not force:
            if not self._changed:
                return SaveResult(self.id)
            field_values = {
                field_name: value
                for field_name, value in field_values.items()
                if self._changed.get(field_name)
            }

        self.meta.table.update(self.id, field_values, typecast=self.meta.typecast)
        self._changed.clear()
        return SaveResult(
            self.id, forced=force, updated=True, field_names=set(field_values)
        )

    def delete(self) -> bool:
        """
        Delete the record.

        Raises:
            ValueError: if the record does not exist.
        """
        if not self.id:
            raise ValueError("cannot be deleted because it does not have id")
        table = self.meta.table
        result = table.delete(self.id)
        self._deleted = True
        # Is it even possible to get "deleted" False?
        return bool(result["deleted"])

    @classmethod
    def all(cls, *, memoize: Optional[bool] = None, **kwargs: Any) -> List[SelfType]:
        """
        Retrieve all records for this model. For all supported
        keyword arguments, see :meth:`Table.all <pyairtable.Table.all>`.

        Args:
            memoize: |kwarg_orm_memoize|
        """
        kwargs.update(cls.meta.request_kwargs)
        return [
            cls.from_record(record, memoize=memoize)
            for record in cls.meta.table.all(**kwargs)
        ]

    @classmethod
    def first(
        cls, *, memoize: Optional[bool] = None, **kwargs: Any
    ) -> Optional[SelfType]:
        """
        Retrieve the first record for this model. For all supported
        keyword arguments, see :meth:`Table.first <pyairtable.Table.first>`.

        Args:
            memoize: |kwarg_orm_memoize|
        """
        kwargs.update(cls.meta.request_kwargs)
        if record := cls.meta.table.first(**kwargs):
            return cls.from_record(record, memoize=memoize)
        return None

    @classmethod
    def _maybe_memoize(cls, instance: SelfType, memoize: Optional[bool]) -> None:
        """
        If memoization is enabled, save the instance to the memoization cache.
        """
        memoize = cls.meta.memoize if memoize is None else memoize
        if memoize:
            cls._memoized[instance.id] = instance

    def to_record(self, only_writable: bool = False) -> RecordDict:
        """
        Build a :class:`~pyairtable.api.types.RecordDict` to represent this instance.

        This method converts internal field values into values expected by Airtable.
        For example, a ``datetime`` value from :class:`~pyairtable.orm.fields.DatetimeField`
        is converted into an ISO 8601 string.

        Args:
            only_writable: If ``True``, the result will exclude any
                values which are associated with readonly fields.
        """
        map_ = self._field_name_descriptor_map()
        fields = {
            field: None if value is None else map_[field].to_record_value(value)
            for field, value in self._fields.items()
            if not (map_[field].readonly and only_writable)
        }
        ct = datetime_to_iso_str(self.created_time) if self.created_time else ""
        return {"id": self.id, "createdTime": ct, "fields": fields}

    @classmethod
    def from_record(
        cls, record: RecordDict, *, memoize: Optional[bool] = None
    ) -> SelfType:
        """
        Create an instance from a record dict.

        Args:
            record: The record data from the Airtable API.
            memoize: |kwarg_orm_memoize|
        """
        name_field_map = cls._field_name_descriptor_map()
        # Convert Column Names into model field names
        field_values = {
            # Use field's to_internal_value to cast into model fields
            field: (
                name_field_map[field].to_internal_value(value)
                if value is not None
                else None
            )
            for (field, value) in record["fields"].items()
            # Silently proceed if Airtable returns fields we don't recognize
            if field in name_field_map
        }
        # Since instance(**field_values) will perform validation and fail on
        # any readonly fields, instead we directly set instance._fields.
        instance = cls(id=record["id"])
        instance._fields = field_values
        instance._fetched = True
        instance.created_time = datetime_from_iso_str(record["createdTime"])
        cls._maybe_memoize(instance, memoize)
        return instance

    @classmethod
    def from_id(
        cls,
        record_id: RecordId,
        *,
        fetch: bool = True,
        memoize: Optional[bool] = None,
    ) -> SelfType:
        """
        Create an instance from a record ID.

        Args:
            record_id: |arg_record_id|
            fetch: |kwarg_orm_fetch|
            memoize: |kwarg_orm_memoize|
        """
        try:
            instance = cast(SelfType, cls._memoized[record_id])  # type: ignore[redundant-cast]
        except KeyError:
            instance = cls(id=record_id)
        if fetch and not instance._fetched:
            instance.fetch()
        cls._maybe_memoize(instance, memoize)
        return instance

    def fetch(self) -> None:
        """
        Fetch field values from the API and resets instance field values.
        """
        if not self.id:
            raise ValueError("cannot be fetched because instance does not have an id")

        record = self.meta.table.get(self.id)
        unused = self.from_record(record, memoize=False)
        self._fields = unused._fields
        self._changed.clear()
        self._fetched = True
        self.created_time = unused.created_time

    @classmethod
    def from_ids(
        cls,
        record_ids: Iterable[RecordId],
        *,
        fetch: bool = True,
        memoize: Optional[bool] = None,
    ) -> List[SelfType]:
        """
        Create a list of instances from record IDs. If any record IDs returned
        are invalid this will raise a KeyError, but only *after* retrieving all
        other valid records from the API.

        Args:
            record_ids: |arg_record_id|
            fetch: |kwarg_orm_fetch|
            memoize: |kwarg_orm_memoize|
        """
        if not fetch:
            return [cls.from_id(record_id, fetch=False) for record_id in record_ids]

        record_ids = list(record_ids)
        by_id: Dict[RecordId, SelfType] = {}

        if cls._memoized:
            for record_id in record_ids:
                try:
                    by_id[record_id] = cast(SelfType, cls._memoized[record_id])  # type: ignore[redundant-cast]
                except KeyError:
                    pass

        if remaining := sorted(set(record_ids) - set(by_id)):
            # Only retrieve records that aren't already memoized
            formula = OR(EQ(RECORD_ID(), record_id) for record_id in sorted(remaining))
            by_id.update(
                {
                    record["id"]: cls.from_record(record, memoize=memoize)
                    for record in cls.meta.table.all(formula=formula)
                }
            )

        # Ensure we return records in the same order, and raise KeyError if any are missing
        return [by_id[record_id] for record_id in record_ids]

    @classmethod
    def batch_save(cls, models: List[SelfType]) -> None:
        """
        Save a list of model instances to the Airtable API with as few
        network requests as possible. Can accept a mixture of new records
        (which have not been saved yet) and existing records that have IDs.
        """
        if not all(isinstance(model, cls) for model in models):
            raise TypeError(set(type(model) for model in models))

        create_models = [model for model in models if not model.id]
        update_models = [model for model in models if model.id]
        create_records: List[WritableFields] = [
            record["fields"]
            for model in create_models
            if (record := model.to_record(only_writable=True))
        ]
        update_records: List[UpdateRecordDict] = [
            {"id": record["id"], "fields": record["fields"]}
            for model in update_models
            if (record := model.to_record(only_writable=True))
        ]

        table = cls.meta.table
        table.batch_update(update_records, typecast=cls.meta.typecast)
        created_records = table.batch_create(create_records, typecast=cls.meta.typecast)
        for model, record in zip(create_models, created_records):
            model.id = record["id"]
            model.created_time = datetime_from_iso_str(record["createdTime"])

    @classmethod
    def batch_delete(cls, models: List[SelfType]) -> None:
        """
        Delete a list of model instances from Airtable.

        Raises:
            ValueError: if the model has not been saved to Airtable.
        """
        if not all(model.id for model in models):
            raise ValueError("cannot delete an unsaved model")
        if not all(isinstance(model, cls) for model in models):
            raise TypeError(set(type(model) for model in models))
        cls.meta.table.batch_delete([model.id for model in models])

    def comments(self) -> List[Comment]:
        """
        Return a list of comments on this record.
        See :meth:`Table.comments <pyairtable.Table.comments>`.
        """
        return self.meta.table.comments(self.id)

    def add_comment(self, text: str) -> Comment:
        """
        Add a comment to this record.
        See :meth:`Table.add_comment <pyairtable.Table.add_comment>`.
        """
        return self.meta.table.add_comment(self.id, text)


@dataclass
class _Meta:
    """
    Wrapper around a Model.Meta class that provides easier, typed access to
    configuration values (which may or may not be defined in the original class).
    """

    model: Type[Model]

    @property
    def _config(self) -> Mapping[str, Any]:
        if not (meta := getattr(self.model, "Meta", None)):
            raise AttributeError(f"{self.model.__name__}.Meta must be defined")
        if isinstance(meta, dict):
            return meta
        try:
            return cast(Mapping[str, Any], meta.__dict__)
        except AttributeError:
            raise TypeError(
                f"{self.model.__name__}.Meta must be a dict or class; got {type(meta)}"
            )

    def get(
        self,
        name: str,
        default: Any = None,
        required: bool = False,
        call: bool = True,
        check_types: Optional["_ClassInfo"] = None,
    ) -> Any:
        """
        Given a name, retrieve the model configuration with that name.

        Args:
            default: The default value to use if the name is not defined.
            required: If ``True``, raises ``ValueError`` if the name is undefined or None.
            call: If ``False``, does not execute any callables to retrieve this value;
                  it will consider the callable itself as the value.
            check_types: If set, will raise a ``TypeError`` if the value is not
                         an instance of the given type(s).
        """
        if required and name not in self._config:
            raise ValueError(f"{self.model.__name__}.Meta.{name} must be defined")
        value = self._config.get(name, default)
        if callable(value) and call:
            value = value()
        if required and value is None:
            raise ValueError(f"{self.model.__name__}.Meta.{name} cannot be None")
        if check_types is not None and not isinstance(value, check_types):
            raise TypeError(f"expected {check_types!r}; got {type(value)}")
        return value

    @property
    def api_key(self) -> str:
        return str(self.get("api_key", required=True))

    @property
    def timeout(self) -> Optional[TimeoutTuple]:
        return self.get(  # type: ignore[no-any-return]
            "timeout",
            default=None,
            check_types=(type(None), tuple),
        )

    @property
    def retry_strategy(self) -> Optional[Union[bool, retrying.Retry]]:
        return self.get(  # type: ignore[no-any-return]
            "retry",
            default=True,
            check_types=(type(None), bool, retrying.Retry),
        )

    @cached_property
    def api(self) -> Api:
        return Api(
            self.api_key,
            timeout=self.timeout,
            retry_strategy=self.retry_strategy,
        )

    @property
    def base_id(self) -> str:
        return str(self.get("base_id", required=True))

    @property
    def base(self) -> Base:
        return self.api.base(self.base_id)

    @property
    def table_name(self) -> str:
        return str(self.get("table_name", required=True))

    @property
    def table(self) -> Table:
        return self.base.table(self.table_name)

    @property
    def typecast(self) -> bool:
        return bool(self.get("typecast", default=True))

    @property
    def use_field_ids(self) -> bool:
        return bool(self.get("use_field_ids", default=False))

    @property
    def memoize(self) -> bool:
        return bool(self.get("memoize", default=False))

    @property
    def request_kwargs(self) -> Dict[str, Any]:
        return {
            "user_locale": None,
            "cell_format": "json",
            "time_zone": None,
            "use_field_ids": self.use_field_ids,
        }


@dataclass(frozen=True)
class SaveResult:
    """
    Represents the result of saving a record to the API. The result's
    attributes contain more granular information about the save operation:

        >>> result = model.save()
        >>> result.record_id
        'recWPqD9izdsNvlE'
        >>> result.created
        False
        >>> result.updated
        True
        >>> result.forced
        False
        >>> result.field_names
        {'Name', 'Email'}

    If none of the model's fields have changed, calling :meth:`~pyairtable.orm.Model.save`
    will not perform any API requests and will return a SaveResult with no changes.

        >>> model = YourModel()
        >>> result = model.save()
        >>> result.saved
        True
        >>> second_result = model.save()
        >>> second_result.saved
        False

    For backwards compatibility, instances of SaveResult will evaluate as truthy
    if the record was created, and falsy if the record was not created.
    """

    record_id: RecordId
    created: bool = False
    updated: bool = False
    forced: bool = False
    field_names: Set[FieldName] = dataclasses.field(default_factory=set)

    def __bool__(self) -> bool:
        """
        Returns ``True`` if the record was created. This is for backwards compatibility
        with the behavior of :meth:`~pyairtable.orm.Model.save` prior to the 3.0 release,
        which returned a boolean indicating whether a record was created.
        """
        warnings.warn(
            "Model.save() now returns SaveResult instead of bool; switch"
            " to checking Model.save().created instead before the 4.0 release.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.created

    @property
    def saved(self) -> bool:
        """
        Whether the record was saved to the API. If ``False``, this indicates there
        were no changes to the model and the :meth:`~pyairtable.orm.Model.save`
        operation was not forced.
        """
        return self.created or self.updated
