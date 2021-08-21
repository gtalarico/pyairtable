from datetime import datetime

import pytest
from pyairtable import Table
from pyairtable import formulas as fo
from pyairtable.utils import attachment
from uuid import uuid4


@pytest.mark.integration
def test_integration_table(table, cols):
    # Create / Get
    rec = table.create({cols.TEXT: "A", cols.NUM: 1, cols.BOOL: True})
    rv_get = table.get(rec["id"])
    assert rv_get["fields"][cols.TEXT] == "A"

    # Update
    rv = table.update(rec["id"], {cols.TEXT: "B"})
    assert rv["fields"][cols.TEXT] == "B"
    assert rv["fields"][cols.NUM] == 1

    # Replace
    rv = table.update(rec["id"], {cols.NUM: 2}, replace=True)
    assert rv["fields"] == {cols.NUM: 2}

    # Get all
    records = table.all()
    assert rec["id"] in [r["id"] for r in records]

    # Delete
    rv = table.delete(rec["id"])
    assert rv["deleted"]

    # Batch Create
    COUNT = 15
    records = table.batch_create(
        [{cols.TEXT: "A", cols.NUM: 1, cols.BOOL: True} for _ in range(COUNT)]
    )

    for record in records:
        record["fields"][cols.TEXT] = "C"
    rv_batch_update = table.batch_update(records)
    assert all([r["fields"][cols.TEXT] == "C" for r in rv_batch_update])

    # Batch Delete
    records = table.batch_delete([r["id"] for r in records])
    assert len(records) == COUNT


@pytest.mark.integration
def test_integration_field_equals(table: Table, cols):
    VALUE = "Test {}".format(uuid4())
    rv_create = table.create({cols.TEXT: VALUE})
    rv_first = table.first(formula=fo.match({cols.TEXT: VALUE}))
    assert rv_first and rv_first["id"] == rv_create["id"]


@pytest.mark.integration
def test_integration_formula_datetime(table: Table, cols):
    VALUE = datetime.utcnow()
    str_value = fo.to_airtable_value(VALUE)
    rv_create = table.create({cols.DATETIME: str_value})
    rv_first = table.first(formula=fo.match({cols.DATETIME: str_value}))
    assert rv_first and rv_first["id"] == rv_create["id"]


@pytest.mark.integration
def test_integration_formula_date_filter(table: Table, cols):
    dt = datetime.utcnow()
    date = dt.date()
    date_str = fo.to_airtable_value(date)

    created = []
    for _ in range(2):
        rec = table.create({cols.DATETIME: fo.to_airtable_value(dt)})
        created.append(rec)

    formula = fo.FIND(fo.STR_VALUE(date_str), fo.FIELD(cols.DATETIME))
    rv_all = table.all(formula=formula)
    assert rv_all
    assert set([r["id"] for r in rv_all]) == set([r["id"] for r in created])


@pytest.mark.integration
def test_integration_field_equals_with_quotes(table: Table, cols):
    VALUE = "Contact's Name {}".format(uuid4())
    rv_create = table.create({cols.TEXT: VALUE})
    rv_first = table.first(formula=fo.match({cols.TEXT: VALUE}))
    assert rv_first and rv_first["id"] == rv_create["id"]

    VALUE = 'Some "Quote"  {}'.format(uuid4())
    rv_create = table.create({cols.TEXT: VALUE})
    rv_first = table.first(formula=fo.match({cols.TEXT: VALUE}))
    assert rv_first and rv_first["id"] == rv_create["id"]


@pytest.mark.integration
def test_integration_formula_composition(table: Table, cols):
    text = "Mike's Thing {}".format(uuid4())
    num = 1
    bool_ = True
    rv_create = table.create({cols.TEXT: text, cols.NUM: num, cols.BOOL: bool_})

    formula = fo.AND(
        fo.EQUAL(fo.FIELD(cols.TEXT), fo.to_airtable_value(text)),
        fo.EQUAL(fo.FIELD(cols.NUM), fo.to_airtable_value(num)),
        fo.EQUAL(
            fo.FIELD(cols.BOOL), fo.to_airtable_value(bool_)
        ),  # not needs to be int()
    )
    rv_first = table.first(formula=formula)

    assert rv_first["id"] == rv_create["id"]


@pytest.mark.integration
def test_integration_attachment(table, cols, valid_img_url):
    rec = table.create({cols.ATTACHMENT: [attachment(valid_img_url)]})
    rv_get = table.get(rec["id"])
    assert rv_get["fields"]["attachment"][0]["filename"] == "logo.png"


@pytest.mark.integration
def test_integration_attachment_multiple(table, cols, valid_img_url):
    rec = table.create(
        {
            cols.ATTACHMENT: [
                attachment(valid_img_url, filename="a.jpg"),
                attachment(valid_img_url, filename="b.jpg"),
            ]
        }
    )
    rv_get = table.get(rec["id"])
    assert rv_get["fields"]["attachment"][0]["filename"] == "a.jpg"
    assert rv_get["fields"]["attachment"][1]["filename"] == "b.jpg"
