"""
Tests that pyairtable.api functions/methods return appropriately typed responses.
"""
from typing import TYPE_CHECKING, Iterator, List, Optional

from typing_extensions import assert_type

import pyairtable
import pyairtable.api.types as T

if TYPE_CHECKING:
    # This section does not actually get executed; it is only parsed by mypy.
    access_token = "patFakeAccessToken"
    base_id = "appTheTestingBase"
    table_name = "tblImaginaryTable"
    record_id = "recSomeFakeRecord"
    now = "2023-01-01T00:00:00.0000Z"

    # Ensure the type signatures for pyairtable.Api don't change.
    api = pyairtable.Api(access_token)
    assert_type(api.build_url("foo", "bar"), str)
    assert_type(api.base(base_id), pyairtable.Base)
    assert_type(api.table(base_id, table_name), pyairtable.Table)

    # Ensure the type signatures for pyairtable.Base don't change.
    base = pyairtable.Base(api, base_id)
    assert_type(base.table(table_name), pyairtable.Table)
    assert_type(base.url, str)

    # Ensure the type signatures for pyairtable.Table don't change.
    table = pyairtable.Table(None, base, table_name)
    assert_type(table, pyairtable.Table)
    assert_type(table.get(record_id), T.RecordDict)
    assert_type(table.iterate(), Iterator[List[T.RecordDict]])
    assert_type(table.all(), List[T.RecordDict])
    assert_type(table.first(), Optional[T.RecordDict])
    assert_type(table.create({}), T.RecordDict)
    assert_type(table.update(record_id, {}), T.RecordDict)
    assert_type(table.delete(record_id), T.RecordDeletedDict)
    assert_type(table.batch_create([]), List[T.RecordDict])
    assert_type(table.batch_update([]), List[T.RecordDict])
    assert_type(table.batch_upsert([], []), List[T.RecordDict])
    assert_type(table.batch_delete([]), List[T.RecordDeletedDict])

    # Ensure we can set all kinds of field values
    table.update(record_id, {"Field Name": "name"})
    table.update(record_id, {"Field Name": 1})
    table.update(record_id, {"Field Name": 1.0})
    table.update(record_id, {"Field Name": True})
    table.update(record_id, {"Field Name": None})
    table.update(record_id, {"Field Name": {"id": "usrXXX"}})
    table.update(record_id, {"Field Name": {"email": "alice@example.com"}})
