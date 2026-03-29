"""
pyAirtable provides a number of helper functions for testing code that uses
the Airtable API. These functions are designed to be used with the standard
Python :mod:`unittest.mock` library, and can be used to create fake records,
users, and attachments, as well as to mock the Airtable API itself.
"""

import datetime
import inspect
import mimetypes
import random
import string
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from functools import partialmethod
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
    overload,
)
from unittest import mock

import urllib3
from typing_extensions import Self, TypeAlias

from pyairtable.api import retrying
from pyairtable.api.api import Api, TimeoutTuple
from pyairtable.api.table import Table
from pyairtable.api.types import (
    AnyRecordDict,
    AttachmentDict,
    CollaboratorDict,
    CreateRecordDict,
    FieldName,
    Fields,
    RecordDeletedDict,
    RecordDict,
    RecordId,
    UpdateRecordDict,
    UpsertResultDict,
    WritableFields,
)
from pyairtable.utils import fieldgetter, is_airtable_id


def _now() -> str:
    return datetime.datetime.now().isoformat() + "Z"


def fake_id(type: str = "rec", value: Any = None) -> str:
    """
    Generate a fake Airtable-style ID.

    Args:
        type: the object type prefix, defaults to "rec"
        value: any value to use as the ID, defaults to random letters and digits

    >>> fake_id()
    'rec...'
    >>> fake_id('tbl')
    'tbl...'
    >>> fake_id(value='12345')
    'rec00000000012345'
    """
    if value is None:
        value = "".join(random.sample(string.ascii_letters + string.digits, 14))
    return type + f"{value:0>14}"[:14]


def fake_meta(
    base_id: str = "",
    table_name: str = "",
    api_key: str = "patFakePersonalAccessToken",
    timeout: Optional[TimeoutTuple] = None,
    retry: Optional[Union[bool, retrying.Retry]] = None,
    typecast: bool = True,
    use_field_ids: bool = False,
    memoize: bool = False,
) -> type:
    """
    Generate a ``Meta`` class for inclusion in a ``Model`` subclass.
    """
    attrs = {
        "base_id": base_id or fake_id("app"),
        "table_name": table_name or fake_id("tbl"),
        "api_key": api_key,
        "timeout": timeout,
        "retry": retry,
        "typecast": typecast,
        "use_field_ids": use_field_ids,
        "memoize": memoize,
    }
    return type("Meta", (), attrs)


def fake_record(
    fields: Optional[Fields] = None,
    id: Optional[str] = None,
    **other_fields: Any,
) -> RecordDict:
    """
    Generate a fake record dict with the given field values.

    >>> fake_record({"Name": "Alice"})
    {
        'id': '...',
        'createdTime': '...',
        'fields': {'name': 'Alice'}
    }

    >>> fake_record(name="Alice", id="123")
    {
        'id': 'rec00000000000123',
        'createdTime': '...',
        'fields': {'name': 'Alice'}
    }

    >>> fake_record(name="Alice", id="recABC00000000123")
    {
        'id': 'recABC00000000123',
        'createdTime': '...',
        'fields': {'name': 'Alice'}
    }
    """
    return {
        "id": str(id) if is_airtable_id(id, "rec") else fake_id(value=id),
        "createdTime": _now(),
        "fields": {**(fields or {}), **other_fields},
    }


def fake_user(value: Any = None) -> CollaboratorDict:
    """
    Generate a fake user dict with the given value for an email prefix.

    >>> fake_user("Alice")
    {
        'id': 'usr000000000Alice',
        'email': 'alice@example.com'
        'name': 'Alice'
    }
    """
    id = fake_id("usr", value)
    return {
        "id": id,
        "email": f"{str(value or id).lower()}@example.com",
        "name": str(value or "Fake User"),
    }


def fake_attachment(url: str = "", filename: str = "") -> AttachmentDict:
    """
    Generate a fake attachment dict.

    >>> fake_attachment()
    {
        'id': 'att...',
        'url': 'https://example.com/',
        'filename': 'foo.txt',
        'size': 100,
        'type': 'text/plain',
    }

    >>> fake_attachment('https://example.com/image.png', 'foo.png')
    {
        'id': 'att...',
        'url': 'https://example.com/image.png',
        'filename': 'foo.png',
        'size': 100,
        'type': 'text/plain',
    }
    """
    if not filename:
        filename = (urllib3.util.parse_url(url).path or "").split("/")[-1]
        filename = filename or "foo.txt"
    return {
        "id": fake_id("att"),
        "url": url or "https://example.com/",
        "filename": filename,
        "size": 100,
        "type": mimetypes.guess_type(filename)[0] or "text/plain",
    }


BaseAndTableId: TypeAlias = Tuple[str, str]


class MockAirtable:
    """
    This class acts as a context manager which mocks several pyAirtable APIs,
    so that your tests can operate against tables without making network requests.

    .. code-block:: python

        from pyairtable import Api
        from pyairtable.testing import MockAirtable

        table = Api.base("baseId").table("tableName")

        with MockAirtable() as m:
            m.add_records(table, [{"Name": "Alice"}])
            records = table.all()
            assert len(table.all()) == 1

    If you use pytest, you might want to include this as a fixture.

    .. code-block:: python

        import pytest
        from pyairtable.testing import MockAirtable

        @pytest.fixture(autouse=True)
        def mock_airtable():
            with MockAirtable() as m:
                yield m

        def test_your_function():
            ...

    Not all API methods are supported; if your test calls a method that would
    make a network request, a RuntimeError will be raised instead.

        >>> with MockAirtable() as m:
        ...     table.schema()
        ...
        Traceback (most recent call last): ...
        RuntimeError: unhandled call to Api.request

    You can allow unhandled requests by setting the ``passthrough`` argument to True,
    either on the constructor or temporarily on the MockAirtable instance. This is
    useful when using another library, like `requests-mock <https://requests-mock.readthedocs.io/en/latest/>`_,
    to prepare responses for complex cases (like code that retrieves the schema).

    .. code-block:: python

        def test_your_function(requests_mock, mock_airtable, monkeypatch):
            base = Api.base("baseId")

            # load and cache our mock schema
            requests_mock.get(
                base.meta_url("tables"),
                json={"tables": [...]}
            )
            with mock_airtable.enable_passthrough():
                base.schema()

            # code below will fail if any more unhandled requests are made
            ...

    """

    # The list of APIs that are mocked by this class.
    mocked = [
        "Api.request",
        "Table.iterate",
        "Table.get",
        "Table.create",
        "Table.update",
        "Table.delete",
        "Table.batch_create",
        "Table.batch_update",
        "Table.batch_delete",
        "Table.batch_upsert",
    ]

    # 2-layer mapping of (base, table) IDs --> record IDs --> record dicts.
    records: Dict[BaseAndTableId, Dict[RecordId, RecordDict]]

    _stack: Optional[ExitStack]
    _mocks: Dict[str, Any]

    def __init__(self, passthrough: bool = False) -> None:
        """
        Args:
            passthrough: if True, unmocked methods will still be allowed to
                perform real network requests. If False, they will raise an error.
        """
        self.passthrough = passthrough
        self._reset()

    def _reset(self) -> None:
        self._stack = None
        self._mocks = {}
        self.records = defaultdict(dict)

    def __enter__(self) -> Self:
        if self._stack:
            raise RuntimeError("MockAirtable is not reentrant")
        if hasattr(Api.request, "mock"):
            raise RuntimeError("MockAirtable cannot be nested")
        self._reset()
        self._stack = ExitStack()

        for name in self.mocked:
            side_effect_name = name.replace(".", "_").lower()
            side_effect = getattr(self, f"_{side_effect_name}", None)
            mocked_method = self._mocks[name] = mock.patch(
                f"pyairtable.{name}",
                side_effect=side_effect,
                autospec=True,
            )
            self._stack.enter_context(mocked_method)

        return self

    def __exit__(self, *exc_info: Any) -> None:
        if self._stack:
            self._stack.__exit__(*exc_info)

    @contextmanager
    def set_passthrough(self, allowed: bool) -> Iterator[Self]:
        """
        Context manager that temporarily changes whether unmocked methods
        are allowed to perform real network requests. For convenience, there are
        also shortcuts ``enable_passthrough()`` and ``disable_passthrough()``.

        Usage:

            .. code-block:: python

                with MockAirtable() as m:
                    with m.enable_passthrough():
                        schema = base.schema()
                        hooks = table.webhooks()

                    # no more network requests allowed
                    ...

        Args:
            allowed: If ``True``, unmocked methods will be allowed to perform real
                network requests within this context manager. If ``False``,
                they will not be allowed.
        """
        original = self.passthrough
        self.passthrough = allowed
        try:
            yield self
        finally:
            self.passthrough = original

    enable_passthrough = partialmethod(set_passthrough, True)
    disable_passthrough = partialmethod(set_passthrough, False)

    @overload
    def add_records(
        self,
        base_id: str,
        table_id_or_name: str,
        /,
        records: Iterable[Dict[str, Any]],
    ) -> List[RecordDict]: ...

    @overload
    def add_records(
        self,
        table: Table,
        /,
        records: Iterable[Dict[str, Any]],
    ) -> List[RecordDict]: ...

    def add_records(self, *args: Any, **kwargs: Any) -> List[RecordDict]:
        """
        Add a list of records to the mock Airtable instance. These will be returned
        from methods like :meth:`~pyairtable.Table.all` and :meth:`~pyairtable.Table.get`.

        Can be called with either a base ID and table name,
        or an instance of :class:`~pyairtable.Table`:

        .. code-block::

            m = MockAirtable()
            m.add_records("baseId", "tableName", [{"Name": "Alice"}])
            m.add_records(table, records=[{"id": "recFake", {"Name": "Alice"}}])

        .. note::

            The parameters to :meth:`~pyairtable.Table.all` are not supported by MockAirtable,
            and constraints like ``formula=`` and ``limit=`` will be ignored. It is assumed
            that you are adding records to specifically test a particular use case.
            MockAirtable is not a full in-memory replacement for the Airtable API.

        Args:
            base_id: |arg_base_id|
                *This must be the first positional argument.*
            table_id_or_name: |arg_table_id_or_name|
                This should be the same ID or name used in the code under test.
                *This must be the second positional argument.*
            table: An instance of :class:`~pyairtable.Table`.
                *This is an alternative to providing base and table IDs,
                and must be the first positional argument.*
            records: A sequence of :class:`~pyairtable.api.types.RecordDict`,
                :class:`~pyairtable.api.types.UpdateRecordDict`,
                :class:`~pyairtable.api.types.CreateRecordDict`,
                or :class:`~pyairtable.api.types.Fields`.
        """
        base_id, table_name, records = _extract_args(args, kwargs, ["records"])
        coerced = [coerce_fake_record(record) for record in records]
        self.records[(base_id, table_name)].update(
            {record["id"]: record for record in coerced}
        )
        return coerced

    @overload
    def set_records(
        self,
        base_id: str,
        table_id_or_name: str,
        /,
        records: Iterable[Dict[str, Any]],
    ) -> None: ...

    @overload
    def set_records(
        self,
        table: Table,
        /,
        records: Iterable[Dict[str, Any]],
    ) -> None: ...

    def set_records(self, *args: Any, **kwargs: Any) -> None:
        """
        Set the mock records for a particular base and table, replacing any existing records.
        See :meth:`~MockAirtable.add_records` for more information.

        Args:
            base_id: |arg_base_id|
                *This must be the first positional argument.*
            table_id_or_name: |arg_table_id_or_name|
                This should be the same ID or name used in the code under test.
                *This must be the second positional argument.*
            table: An instance of :class:`~pyairtable.Table`.
                *This is an alternative to providing base and table IDs,
                and must be the first positional argument.*
            records: A sequence of :class:`~pyairtable.api.types.RecordDict`,
                :class:`~pyairtable.api.types.UpdateRecordDict`,
                :class:`~pyairtable.api.types.CreateRecordDict`,
                or :class:`~pyairtable.api.types.Fields`.
        """
        base_id, table_name, records = _extract_args(args, kwargs, ["records"])
        self.records[(base_id, table_name)].clear()
        self.add_records(base_id, table_name, records=records)

    def clear(self) -> None:
        """
        Clear all records from the mock Airtable instance.
        """
        self.records.clear()

    # side effects

    def _api_request(self, api: Api, method: str, url: str, **kwargs: Any) -> Any:
        if not self.passthrough:
            raise RuntimeError("unhandled call to Api.request")
        mocked = self._mocks["Api.request"]
        return mocked.temp_original(api, method, url, **kwargs)

    def _table_iterate(self, table: Table, **options: Any) -> List[List[RecordDict]]:
        return [list(self.records[(table.base.id, table.name)].values())]

    def _table_get(self, table: Table, record_id: str, **options: Any) -> RecordDict:
        return self.records[(table.base.id, table.name)][record_id]

    def _table_create(
        self,
        table: Table,
        record: CreateRecordDict,
        **kwargs: Any,
    ) -> RecordDict:
        records = self.records[(table.base.id, table.name)]
        record = coerce_fake_record(record)
        while record["id"] in records:
            record["id"] = fake_id()  # pragma: no cover
        records[record["id"]] = record
        return record

    def _table_update(
        self,
        table: Table,
        record_id: RecordId,
        fields: WritableFields,
        **kwargs: Any,
    ) -> RecordDict:
        exists = self.records[(table.base.id, table.name)][record_id]
        exists["fields"].update(fields)
        return exists

    def _table_delete(self, table: Table, record_id: RecordId) -> RecordDeletedDict:
        self.records[(table.base.id, table.name)].pop(record_id)
        return {"id": record_id, "deleted": True}

    def _table_batch_create(
        self,
        table: Table,
        records: Iterable[CreateRecordDict],
        **kwargs: Any,
    ) -> List[RecordDict]:
        return [self._table_create(table, record) for record in records]

    def _table_batch_update(
        self,
        table: Table,
        records: Iterable[UpdateRecordDict],
        **kwargs: Any,
    ) -> List[RecordDict]:
        return [
            self._table_update(table, record["id"], record["fields"])
            for record in records
        ]

    def _table_batch_delete(
        self,
        table: Table,
        record_ids: Iterable[RecordId],
    ) -> List[RecordDeletedDict]:
        return [self._table_delete(table, record_id) for record_id in record_ids]

    def _table_batch_upsert(
        self,
        table: Table,
        records: Iterable[AnyRecordDict],
        key_fields: Iterable[FieldName],
        **kwargs: Any,
    ) -> UpsertResultDict:
        """
        Perform a batch upsert operation on the mocked records for the table.
        """
        key = fieldgetter(*key_fields)
        existing_by_id = self.records[(table.base.id, table.name)]
        existing_by_key = {key(r): r for r in existing_by_id.values()}
        result: UpsertResultDict = {
            "updatedRecords": [],
            "createdRecords": [],
            "records": [],
        }

        for record in records:
            existing_record: Optional[RecordDict]
            if "id" in record:
                record_id = str(record.get("id"))
                existing_record = existing_by_id[record_id]
                existing_record["fields"].update(record["fields"])
                result["updatedRecords"].append(record_id)
                result["records"].append(existing_record)
            elif existing_record := existing_by_key.get(key(record)):
                existing_record["fields"].update(record["fields"])
                result["updatedRecords"].append(existing_record["id"])
                result["records"].append(existing_record)
            else:
                created_record = self._table_create(table, record)
                result["createdRecords"].append(created_record["id"])
                result["records"].append(created_record)

        return result


def coerce_fake_record(record: Union[AnyRecordDict, Fields]) -> RecordDict:
    """
    Coerce a record dict or field mapping to the expected format for
    an Airtable record, creating a fake ID and createdTime if necessary.

    >>> coerce_fake_record({"Name": "Alice"})
    {'id': 'rec000...', 'createdTime': '...', 'fields': {'Name': 'Alice'}}
    """
    if "fields" not in record:
        record = {"fields": cast(Fields, record)}
    return {
        "id": str(record.get("id") or fake_id()),
        "createdTime": str(record.get("createdTime") or _now()),
        "fields": record["fields"],
    }


def _extract_args(
    args: Sequence[Any],
    kwargs: Dict[str, Any],
    extract: Optional[Sequence[str]] = None,
) -> Tuple[Any, ...]:
    """
    Convenience function for functions/methods which accept either
    a Table or a (base_id, table_name) as their first posargs.
    """
    extract = extract or []
    extracted = set()
    caller = inspect.stack()[1].function

    if type(args[0]) is Table:
        args = (args[0].base.id, args[0].name, *args[1:])

    argtypes = tuple(type(arg) for arg in args)
    if argtypes[:2] != (str, str):
        raise TypeError(
            f"{caller} expected (str, str, ...), got ({', '.join(t.__name__ for t in argtypes)})"
        )

    for extract_name in extract:
        if extract_name in kwargs:
            extracted.add(extract_name)
            args = (*args, kwargs.pop(extract_name))

    if kwargs:
        raise TypeError(
            f"{caller} got unexpected keyword arguments: {', '.join(kwargs)}"
        )
    if len(args) < len(extract) + 2 and len(extracted) < len(extract):
        missing = set(extract) - extracted
        raise TypeError(f"{caller} missing keyword arguments: {', '.join(missing)}")

    return tuple(args)
