import pytest
import requests

from pyairtable import Api, Base, Table
from pyairtable.metadata import get_api_bases, get_base_schema, get_table_schema

pytestmark = [pytest.mark.integration]


def test_api_bases(api: Api, base_id: str, base_name: str, table_name: str):
    bases = api.bases()
    assert bases[base_id].name == base_name
    assert bases[base_id].table(table_name).name == table_name


def test_api_base(api: Api, base_id: str, base_name: str):
    base = api.base(base_id, validate=True)
    assert base.name == base_name


def test_base_collaborators(base: Base):
    with pytest.raises(
        requests.HTTPError,
        match=r"collaborators\(\) requires an enterprise billing plan",
    ):
        base.info()


def test_base_schema(base: Base, table_name: str):
    schema = base.schema()
    assert table_name in [t.name for t in schema.tables]
    assert schema.table(table_name).name == table_name


def test_table_schema(base: Base, table_name: str, cols):
    schema = base.table(table_name).schema()
    assert cols.TEXT in [f.name for f in schema.fields]
    assert schema.field(cols.TEXT).id == cols.TEXT_ID
    assert schema.field(cols.TEXT_ID).name == cols.TEXT


def test_deprecated_get_api_bases(base: Base, base_name: str):
    with pytest.warns(DeprecationWarning):
        rv = get_api_bases(base)
    assert base_name in [b["name"] for b in rv["bases"]]


def test_deprecated_get_base_schema(base: Base):
    with pytest.warns(DeprecationWarning):
        rv = get_base_schema(base)
    assert sorted(table["name"] for table in rv["tables"]) == [
        "Address",
        "Contact",
        "EVERYTHING",
        "TEST_TABLE",
    ]


def test_deprecated_get_table_schema(table: Table):
    with pytest.warns(DeprecationWarning):
        rv = get_table_schema(table)
    assert rv and rv["name"] == table.name


def test_deprecated_get_table_schema__invalid_table(table, monkeypatch):
    monkeypatch.setattr(table, "name", "DoesNotExist")
    with pytest.warns(DeprecationWarning):
        assert get_table_schema(table) is None
