import os

import pytest

from pyairtable import Api, Base, Table


@pytest.fixture
def valid_img_url():
    return "https://github.com/gtalarico/pyairtable/raw/9f243cb0935ad7112859f990434612efdaf49c67/docs/source/_static/logo.png"


@pytest.fixture
def cols():
    class Columns:
        # Table should have these Columns
        TEXT = "text"  # Text
        TEXT_ID = "fldzbVdWW4xJdZ1em"  # for returnFieldsByFieldId
        NUM = "number"  # Number, float
        NUM_ID = "fldFLyuxGuWobyMV2"  # for returnFieldsByFieldId
        BOOL = "boolean"  # Boolean
        DATETIME = "datetime"  # Datetime
        ATTACHMENT = "attachment"  # attachment

    return Columns


@pytest.fixture
def api_key():
    try:
        return os.environ["AIRTABLE_API_KEY"]
    except KeyError:
        pytest.skip("integration test requires AIRTABLE_API_KEY env variable")


@pytest.fixture
def api(api_key) -> Api:
    return Api(api_key)


@pytest.fixture
def base_id():
    return "appaPqizdsNHDvlEm"


@pytest.fixture
def base(api, base_id) -> Base:
    return api.base(base_id)


@pytest.fixture
def base_name():
    return "Test Wrapper"


@pytest.fixture
def table_name():
    return "TEST_TABLE"


@pytest.fixture
def table(base: Base, table_name) -> Table:
    table = base.table(table_name)
    yield table
    records = table.all()
    table.batch_delete([r["id"] for r in records])


@pytest.fixture
def make_meta(api_key, base_id):
    def _make_meta(table_name):
        dct = {
            "api_key": api_key,
            "base_id": base_id,
            "table_name": table_name,
        }
        return type("Meta", (), dct)

    return _make_meta
