"""
Helper functions for writing tests that use the pyairtable library.
"""
import datetime
import random
import string
from contextlib import ExitStack, contextmanager
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple, Union
from unittest import mock

from pyairtable.api.api import Api
from pyairtable.api.table import Table
from pyairtable.api.types import (
    AttachmentDict,
    CollaboratorDict,
    CreateRecordDict,
    Fields,
    RecordDeletedDict,
    RecordDict,
    UpdateRecordDict,
    UpsertResultDict,
    UserAndScopesDict,
    WritableFields,
)


def fake_id(type: str = "rec", value: Any = None) -> str:
    """
    Generates a fake Airtable-style ID.

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
    base_id: str = "appFakeTestingApp",
    table_name: str = "tblFakeTestingTbl",
    api_key: str = "patFakePersonalAccessToken",
) -> type:
    """
    Returns a ``Meta`` class for inclusion in a ``Model`` subclass.
    """
    attrs = {"base_id": base_id, "table_name": table_name, "api_key": api_key}
    return type("Meta", (), attrs)


def fake_record(
    fields: Optional[Fields] = None,
    id: Optional[str] = None,
    **other_fields: Any,
) -> RecordDict:
    """
    Returns a fake record dict with the given field values.

    >>> fake_record({"Name": "Alice"})
    {'id': '...', 'createdTime': '...', 'fields': {'Name': 'Alice'}}

    >>> fake_record(name='Alice', address='123 Fake St')
    {'id': '...', 'createdTime': '...', 'fields': {'name': 'Alice', 'address': '123 Fake St'}}

    >>> fake_record(name='Alice', id='123')
    {'id': 'rec00000000000123', 'createdTime': '...', 'fields': {'name': 'Alice'}}
    """
    return {
        "id": fake_id(value=id),
        "createdTime": datetime.datetime.now().isoformat() + "Z",
        "fields": {**(fields or {}), **other_fields},
    }


def fake_user(value: Any = None) -> CollaboratorDict:
    id = fake_id("usr", value)
    return {"id": id, "email": f"{value or id}@example.com", "name": "Fake User"}


def fake_attachment() -> AttachmentDict:
    return {
        "id": fake_id("att"),
        "url": "https://example.com/",
        "filename": "foo.txt",
        "size": 100,
        "type": "text/plain",
    }


class FakeAirtable:
    """
    Used to mock the Airtable API for testing purposes.

    FakeAirtable uses in-memory data structures to store and retrieve
    instances of :class:`~pyairtable.api.types.RecordDict`. It does not
    implement a lot of the functionality of the Airtable API; it only
    provides a bare minimum to be able to mock common methods which interact
    with the API for testing purposes.
    """

    def __init__(self) -> None:
        self._records: Dict[Tuple[str, str], Dict[str, RecordDict]] = {}
        self._immutable: Set[Tuple[str, str, str]] = set()

    def add_records(
        self,
        base_id: str,
        table_name: str,
        records: Sequence[RecordDict],
        immutable: bool = False,
    ) -> None:
        self._records.setdefault((base_id, table_name), {}).update(
            {record["id"]: record for record in records}
        )
        if immutable:
            self._immutable.update(
                (base_id, table_name, record["id"]) for record in records
            )

    def _get(self, table: Table, record_id: str) -> RecordDict:
        return self._records[(table.base.id, table.name)][record_id]

    def _iterate(self, table: Table, **kwargs: Any) -> Iterator[List[RecordDict]]:
        yield list(self._records[(table.base.id, table.name)].values())

    def _create(
        self, table: Table, fields: WritableFields, **kwargs: Any
    ) -> RecordDict:
        record: RecordDict = {
            "id": fake_id(),
            "createdTime": datetime.datetime.utcnow().isoformat(),
            "fields": fields,
        }
        self.add_records(table.base.id, table.name, [record])
        return record

    def _update(
        self, table: Table, record_id: str, fields: WritableFields, **kwargs: Any
    ) -> RecordDict:
        record = self._records[(table.base.id, table.name)][record_id]
        if (table.base.id, table.name, record_id) not in self._immutable:
            record["fields"].update(fields)
        return record

    def _delete(self, table: Table, record_id: str) -> RecordDeletedDict:
        del self._records[(table.base.id, table.name)][record_id]
        return {"id": record_id, "deleted": True}

    def _batch_create(
        self, table: Table, records: List[WritableFields], **kwargs: Any
    ) -> List[RecordDict]:
        return [self._create(table, fields) for fields in records]

    def _batch_update(
        self, table: Table, records: List[UpdateRecordDict], **kwargs: Any
    ) -> List[RecordDict]:
        return [
            self._update(table, record["id"], record["fields"]) for record in records
        ]

    def _batch_delete(
        self, table: Table, record_ids: List[str]
    ) -> List[RecordDeletedDict]:
        return [self._delete(table, record_id) for record_id in record_ids]

    def _batch_upsert(
        self,
        table: Table,
        records: List[UpdateRecordDict],
        key_fields: List[str],
        **kwargs: Any,
    ) -> UpsertResultDict:
        def key(
            record: Union[CreateRecordDict, UpdateRecordDict, RecordDict]
        ) -> Tuple[Any, ...]:
            return tuple(record["fields"].get(f) for f in key_fields)

        created: Dict[str, RecordDict] = {}
        updated: Dict[str, RecordDict] = {}
        existing = {
            key(record): record
            for record in self._records[(table.base.id, table.name)].values()
        }

        for record in records:
            if "id" not in record and (found := existing.get(key(record))):
                record["id"] = found["id"]
            if "id" in record:
                updated[record["id"]] = self._update(
                    table, record["id"], record["fields"]
                )
                continue
            created[c["id"]] = (c := self._create(table, record["fields"]))

        return {
            "createdRecords": list(created),
            "updatedRecords": list(updated),
            "records": list(created.values()) + list(updated.values()),
        }

    def _whoami(self, api: Api) -> UserAndScopesDict:
        return {"id": "usrX9e810wHn3mMLz"}


@contextmanager
def fake_airtable() -> Iterator[FakeAirtable]:
    """
    Context manager that will mock all pyAirtable API endpoints to avoid making
    network calls and to allow stubbing of basic interactions with pyAirtable.
    """
    fake = FakeAirtable()

    with ExitStack() as stack:
        for target, method in [
            ("pyairtable.Table.get", fake._get),
            ("pyairtable.Table.iterate", fake._iterate),
            ("pyairtable.Table.create", fake._create),
            ("pyairtable.Table.update", fake._update),
            ("pyairtable.Table.delete", fake._delete),
            ("pyairtable.Table.batch_create", fake._batch_create),
            ("pyairtable.Table.batch_update", fake._batch_update),
            ("pyairtable.Table.batch_delete", fake._batch_delete),
            ("pyairtable.Table.batch_upsert", fake._batch_upsert),
            ("pyairtable.Api.whoami", fake._whoami),
        ]:
            stack.enter_context(mock.patch(target, autospec=True, side_effect=method))

        yield fake
