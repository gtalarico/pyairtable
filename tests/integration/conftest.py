import os

import pytest

from pyairtable import Api, Base, Table

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
def api() -> Api:
    return Api(os.environ["AIRTABLE_API_KEY"])


@pytest.fixture
def base(api: Api) -> Base:
    return api.base(BASE_ID)


@pytest.fixture
def table(base: Base) -> Table:
    table = base.table("TEST_TABLE")
    yield table
    records = table.all()
    table.batch_delete([r["id"] for r in records])
