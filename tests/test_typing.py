"""
Tests that pyairtable.api functions/methods return appropriately typed responses.
"""
from typing import TYPE_CHECKING, Iterator, List, Optional

from typing_extensions import assert_type

import pyairtable.api
import pyairtable.api.types as T

if TYPE_CHECKING:
    # This section does not actually get executed; it is only parsed by mypy.
    access_token = "patFakeAccessToken"
    base_id = "appTheTestingBase"
    table_name = "tblImaginaryTable"
    record_id = "recSomeFakeRecord"
    now = "2023-01-01T00:00:00.0000Z"

    # Ensure the type signatures for pyairtable.api.Api don't change.
    api = pyairtable.api.Api(access_token)
    assert_type(api.get(base_id, table_name, record_id), T.RecordDict)
    assert_type(api.iterate(base_id, table_name), Iterator[List[T.RecordDict]])
    assert_type(api.all(base_id, table_name), List[T.RecordDict])
    assert_type(api.first(base_id, table_name), Optional[T.RecordDict])
    assert_type(api.create(base_id, table_name, {}), T.RecordDict)
    assert_type(api.update(base_id, table_name, record_id, {}), T.RecordDict)
    assert_type(api.delete(base_id, table_name, record_id), T.RecordDeletedDict)
    assert_type(api.batch_create(base_id, table_name, []), List[T.RecordDict])
    assert_type(api.batch_update(base_id, table_name, []), List[T.RecordDict])
    assert_type(api.batch_upsert(base_id, table_name, [], []), List[T.RecordDict])
    assert_type(api.batch_delete(base_id, table_name, []), List[T.RecordDeletedDict])
    assert_type(api.get_base(base_id), pyairtable.api.Base)
    assert_type(api.get_table(base_id, table_name), pyairtable.api.Table)

    # Ensure the type signatures for pyairtable.api.Base don't change.
    base = pyairtable.api.Base(access_token, base_id)
    assert_type(base.get(table_name, record_id), T.RecordDict)
    assert_type(base.iterate(table_name), Iterator[List[T.RecordDict]])
    assert_type(base.all(table_name), List[T.RecordDict])
    assert_type(base.first(table_name), Optional[T.RecordDict])
    assert_type(base.create(table_name, {}), T.RecordDict)
    assert_type(base.update(table_name, record_id, {}), T.RecordDict)
    assert_type(base.delete(table_name, record_id), T.RecordDeletedDict)
    assert_type(base.batch_create(table_name, []), List[T.RecordDict])
    assert_type(base.batch_update(table_name, []), List[T.RecordDict])
    assert_type(base.batch_upsert(table_name, [], []), List[T.RecordDict])
    assert_type(base.batch_delete(table_name, []), List[T.RecordDeletedDict])
    assert_type(base.get_table(table_name), pyairtable.api.Table)

    # Ensure the type signatures for pyairtable.api.Table don't change.
    table = pyairtable.api.Table(access_token, base_id, table_name)
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
