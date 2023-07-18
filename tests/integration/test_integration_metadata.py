import pytest

from pyairtable import Base, Table
from pyairtable.metadata import get_api_bases, get_base_schema, get_table_schema

pytestmark = [pytest.mark.integration]


def test_get_api_bases(base: Base, base_name: str):
    rv = get_api_bases(base)
    assert base_name in [b["name"] for b in rv["bases"]]


def test_get_base_schema(base: Base):
    rv = get_base_schema(base)
    assert sorted(table["name"] for table in rv["tables"]) == [
        "Address",
        "Contact",
        "EVERYTHING",
        "TEST_TABLE",
    ]


def test_get_table_schema(table: Table):
    rv = get_table_schema(table)
    assert rv and rv["name"] == table.name


def test_get_table_schema__invalid_table(table, monkeypatch):
    monkeypatch.setattr(table, "name", "DoesNotExist")
    assert get_table_schema(table) is None
