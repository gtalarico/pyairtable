import pytest
import requests

from pyairtable import Api, Base

pytestmark = [pytest.mark.integration]


def test_api_bases(api: Api, base_id: str, base_name: str, table_name: str):
    bases = {base.id: base for base in api.bases()}
    assert bases[base_id].name == base_name
    assert bases[base_id].table(table_name).name == table_name


def test_api_base(api: Api, base_id: str, base_name: str):
    base = api.base(base_id, validate=True)
    assert base.name == base_name


def test_base_info(base: Base):
    with pytest.raises(
        requests.HTTPError,
        match=r"Base.collaborators\(\) requires an enterprise billing plan",
    ):
        base.collaborators()


def test_base_schema(base: Base, table_name: str):
    schema = base.schema()
    assert table_name in [t.name for t in schema.tables]
    assert schema.table(table_name).name == table_name


def test_table_schema(base: Base, table_name: str, cols):
    schema = base.table(table_name).schema()
    assert cols.TEXT in [f.name for f in schema.fields]
    assert schema.field(cols.TEXT).id == cols.TEXT_ID
    assert schema.field(cols.TEXT_ID).name == cols.TEXT
