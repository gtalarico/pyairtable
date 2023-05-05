import os

import pytest

from pyairtable import Base, Table

BASE_ID = "appaPqizdsNHDvlEm"


@pytest.fixture
def base_name():
    return "Test Wrapper"


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
def base():
    base_id = BASE_ID
    base = Base(os.environ["AIRTABLE_API_KEY"], base_id)
    yield base
    table_name = "TEST_TABLE"
    records = base.all(table_name)
    base.batch_delete(table_name, [r["id"] for r in records])


@pytest.fixture
def table():
    base_id = BASE_ID
    table_name = "TEST_TABLE"
    table = Table(os.environ["AIRTABLE_API_KEY"], base_id, table_name)
    yield table
    records = table.all()
    table.batch_delete([r["id"] for r in records])
