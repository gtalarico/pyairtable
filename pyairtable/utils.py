import inspect
import re
import textwrap
import warnings
from datetime import date, datetime
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
    cast,
)

import requests
from typing_extensions import ParamSpec, Protocol

from pyairtable.api.types import AnyRecordDict, CreateAttachmentByUrl, FieldValue

P = ParamSpec("P")
R = TypeVar("R", covariant=True)
T = TypeVar("T")
C = TypeVar("C", contravariant=True)
F = TypeVar("F", bound=Callable[..., Any])


def datetime_to_iso_str(value: datetime) -> str:
    """
    Convert ``datetime`` object into Airtable compatible ISO 8601 string
    e.g. "2014-09-05T12:34:56.000Z"

    Args:
        value: datetime object
    """
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def datetime_from_iso_str(value: str) -> datetime:
    """
    Convert an ISO 8601 datetime string into a ``datetime`` object.

    Args:
        value: datetime string, e.g. "2014-09-05T07:00:00.000Z"
    """
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def date_to_iso_str(value: Union[date, datetime]) -> str:
    """
    Convert a ``date`` or ``datetime`` into an Airtable-compatible ISO 8601 string

    Args:
        value: date or datetime object, e.g. "2014-09-05"
    """
    return value.strftime("%Y-%m-%d")


def date_from_iso_str(value: str) -> date:
    """
    Convert ISO 8601 date string into a ``date`` object.

    Args:
        value: date string, e.g. "2014-09-05"
    """
    return datetime.strptime(value, "%Y-%m-%d").date()


def attachment(url: str, filename: str = "") -> CreateAttachmentByUrl:
    """
    Build a ``dict`` in the expected format for creating attachments.

    When creating an attachment, ``url`` is required, and ``filename`` is optional.
    Airtable will download the file at the given url and keep its own copy of it.
    All other attachment object properties will be generated server-side soon afterward.

    Note:
        Attachment field values **must** be an array of
        :class:`~pyairtable.api.types.AttachmentDict` or
        :class:`~pyairtable.api.types.CreateAttachmentByUrl`;
        it is not valid to pass a single item to the API.

    Usage:
        >>> table = Table(...)
        >>> profile_url = "https://example.com/profile.jpg"
        >>> rec = table.create({"Profile Photo": [attachment(profile_url)]})
        {
            'id': 'recZXOZ5gT9vVGHfL',
            'fields': {
                'attachment': [
                    {
                        'id': 'attu6kbaST3wUuNTA',
                        'url': 'https://content.airtable.com/...',
                        'filename': 'profile.jpg'
                    }
                ]
            },
            'createdTime': '2021-08-21T22:28:36.000Z'
        }


    """
    warnings.warn(
        "attachment(url, filename) is deprecated; use {'url': url, 'filename': filename} instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return {"url": url} if not filename else {"url": url, "filename": filename}


def chunked(iterable: Sequence[T], chunk_size: int) -> Iterator[Sequence[T]]:
    """
    Break a sequence into chunks.

    Args:
        iterable: Any sequence.
        chunk_size: Maximum items to yield per chunk.
    """
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i : i + chunk_size]


def is_airtable_id(value: Any, prefix: str = "") -> bool:
    """
    Check whether the given value is an Airtable ID.

    Args:
        value: The value to check.
        prefix: If provided, the ID must have the given prefix.
    """
    if not isinstance(value, str):
        return False
    if prefix and not value.startswith(prefix):
        return False
    return len(value) == 17


is_record_id = partial(is_airtable_id, prefix="rec")
is_base_id = partial(is_airtable_id, prefix="app")
is_table_id = partial(is_airtable_id, prefix="tbl")
is_field_id = partial(is_airtable_id, prefix="fld")
is_user_id = partial(is_airtable_id, prefix="usr")


def enterprise_only(wrapped: F, /, modify_docstring: bool = True) -> F:
    """
    Wrap a function or method so that if Airtable returns a 404,
    we will annotate the error with a helpful note to the user.
    """

    if modify_docstring:
        _prepend_docstring_text(wrapped, "|enterprise_only|")

    # Allow putting the decorator on a class
    if inspect.isclass(wrapped):
        for name, obj in vars(wrapped).items():
            if inspect.isfunction(obj):
                setattr(wrapped, name, enterprise_only(obj))
        return cast(F, wrapped)

    @wraps(wrapped)
    def _decorated(*args: Any, **kwargs: Any) -> Any:
        try:
            return wrapped(*args, **kwargs)
        except requests.exceptions.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                exc.args = (
                    *exc.args,
                    f"NOTE: {wrapped.__qualname__}() requires an enterprise billing plan.",
                )
            raise exc

    return _decorated  # type: ignore[return-value]


def _prepend_docstring_text(obj: Any, text: str) -> None:
    if not (doc := obj.__doc__):
        return
    doc = doc.lstrip("\n")
    if has_leading_spaces := re.match(r"^\s+", doc):
        text = textwrap.indent(text, has_leading_spaces[0])
    obj.__doc__ = f"{text}\n\n{doc}"


def _append_docstring_text(obj: Any, text: str) -> None:
    if not (doc := obj.__doc__):
        return
    doc = doc.rstrip("\n")
    if has_leading_spaces := re.match(r"^\s+", doc):
        text = textwrap.indent(text, has_leading_spaces[0])
    obj.__doc__ = f"{doc}\n\n{text}"


def docstring_from(obj: Any, append: str = "") -> Callable[[F], F]:
    def _wrapper(func: F) -> F:
        func.__doc__ = obj.__doc__ + append
        return func

    return _wrapper


class _FetchMethod(Protocol, Generic[C, R]):
    def __get__(self, instance: C, owner: Any) -> Callable[..., R]: ...

    def __call__(self_, self: C, *, force: bool = False) -> R: ...


def cache_unless_forced(func: Callable[[C], R]) -> _FetchMethod[C, R]:
    """
    Wrap a method (e.g. ``Base.shares()``) in a decorator that will save
    a memoized version of the return value for future reuse, but will also
    allow callers to pass ``force=True`` to recompute the memoized version.
    """

    attr = f"_{func.__name__}"
    if attr.startswith("__"):
        attr = "_cached_" + attr.lstrip("_")

    @wraps(func)
    def _inner(self: C, *, force: bool = False) -> R:
        if force or getattr(self, attr, None) is None:
            setattr(self, attr, func(self))
        return cast(R, getattr(self, attr))

    _inner.__annotations__["force"] = bool
    _append_docstring_text(_inner, "Args:\n\tforce: |kwarg_force_metadata|")

    return cast(_FetchMethod[C, R], _inner)


def coerce_iso_str(value: Any) -> Optional[str]:
    """
    Given an input that might be a date or datetime, or an ISO 8601 formatted str,
    convert the value into an ISO 8601 formatted str.
    """
    if value is None:
        return value
    if isinstance(value, str):
        datetime.fromisoformat(value)  # validates type, nothing more
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"cannot coerce {type(value)} into ISO 8601 str")


def coerce_list_str(value: Optional[Union[str, Iterable[str]]]) -> List[str]:
    """
    Given an input that is either a str or an iterable of str, return a list.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def fieldgetter(
    *fields: str,
    required: Union[bool, Iterable[str]] = False,
) -> Callable[[AnyRecordDict], Any]:
    """
    Create a function that extracts ID, created time, or field values from a record.
    Intended to be used in similar situations as
    `operator.itemgetter <https://docs.python.org/3/library/operator.html#operator.itemgetter>`_.

    >>> record = {"id": "rec001", "fields": {"Name": "Alice"}}
    >>> fieldgetter("Name")(record)
    'Alice'
    >>> fieldgetter("id")(record)
    'rec001'
    >>> fieldgetter("id", "Name", "Missing")(record)
    ('rec001', 'Alice', None)

    Args:
        fields: The field names to extract from the record. The values
            ``"id"`` and ``"createdTime"`` are special cased; all other
            values are interpreted as field names.
        required: If True, will raise KeyError if a value is missing.
            If False, missing values will return as None.
            If a sequence of field names is provided, only those names
            will be required.
    """
    if isinstance(required, str):
        required = {required}
    elif required is True:
        required = set(fields)
    elif required is False:
        required = []
    else:
        required = set(required)

    def _get_field(record: AnyRecordDict, field: str) -> FieldValue:
        src = record if field in ("id", "createdTime") else record["fields"]
        if field in required and field not in src:
            raise KeyError(field)
        return src.get(field)

    if len(fields) == 1:
        return partial(_get_field, field=fields[0])

    def _getter(record: AnyRecordDict) -> Any:
        return tuple(_get_field(record, field) for field in fields)

    return _getter


# [[[cog]]]
# import re
# contents = "".join(open(cog.inFile).readlines()[:cog.firstLineNum])
# functions = re.findall(r"^def ([a-z]\w+)\(", contents, re.MULTILINE)
# partials = re.findall(r"^([A-Za-z]\w+) = partial\(", contents, re.MULTILINE)
# constants = re.findall(r"^([A-Z][A-Z_]+) = ", contents, re.MULTILINE)
# cog.outl("__all__ = [")
# for name in sorted(functions + partials + constants):
#     cog.outl(f'    "{name}",')
# cog.outl("]")
# [[[out]]]
__all__ = [
    "attachment",
    "cache_unless_forced",
    "chunked",
    "coerce_iso_str",
    "coerce_list_str",
    "date_from_iso_str",
    "date_to_iso_str",
    "datetime_from_iso_str",
    "datetime_to_iso_str",
    "docstring_from",
    "enterprise_only",
    "fieldgetter",
    "is_airtable_id",
    "is_base_id",
    "is_field_id",
    "is_record_id",
    "is_table_id",
    "is_user_id",
]
# [[[end]]] (checksum: 7cf950d19fee128ae3f395ddbc475c0f)
