from datetime import datetime
from uuid import uuid4

import pytest

from pyairtable import Table
from pyairtable import formulas as fo
from pyairtable.utils import attachment

pytestmark = [pytest.mark.integration]


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
    assert cols.NUM in records[0]["fields"]  # col name in "fields"

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


def test_return_fields_by_field_id(table: Table, cols):
    """
    Test that we can get, create, and update records by field ID vs. name.

    See https://github.com/gtalarico/pyairtable/issues/194
    """
    # Create one record with return_fields_by_field_id=True
    record = table.create({cols.TEXT_ID: "Hello"}, return_fields_by_field_id=True)
    assert record["fields"][cols.TEXT_ID] == "Hello"

    # Updating a record by field ID does not require any special parameters,
    # but the return value will have field names (not IDs).
    updated = table.update(record["id"], {cols.TEXT_ID: "Goodbye"})
    assert updated["fields"][cols.TEXT] == "Goodbye"

    # This is not supported (422 Client Error: Unprocessable Entity for url)
    # updated = table.update(
    #     record["id"],
    #     {cols.TEXT_ID: "Goodbye"},
    #     return_fields_by_field_id=True,
    # )
    # assert updated["fields"][cols.TEXT_ID] == "Goodbye"

    # Create multiple records with return_fields_by_field_id=True
    records = table.batch_create(
        [
            {cols.TEXT_ID: "Alpha"},
            {cols.TEXT_ID: "Bravo"},
            {cols.TEXT_ID: "Charlie"},
        ],
        return_fields_by_field_id=True,
    )
    assert records[0]["fields"][cols.TEXT_ID] == "Alpha"
    assert records[1]["fields"][cols.TEXT_ID] == "Bravo"
    assert records[2]["fields"][cols.TEXT_ID] == "Charlie"

    # Update multiple records with return_fields_by_field_id=True
    updates = [
        dict(
            record,
            fields={cols.TEXT_ID: "Hello, " + record["fields"][cols.TEXT_ID]},
        )
        for record in records
    ]
    updated = table.batch_update(updates, return_fields_by_field_id=True)
    assert updated[0]["fields"][cols.TEXT_ID] == "Hello, Alpha"
    assert updated[1]["fields"][cols.TEXT_ID] == "Hello, Bravo"
    assert updated[2]["fields"][cols.TEXT_ID] == "Hello, Charlie"


def test_get_records_options(table: Table, cols):
    """
    Test that we pass all valid options to the GET endpoint.
    """
    rec = table.create({cols.TEXT: "abracadabra"})

    # Test that each supported option works via GET
    # (or, at least, that we don't get complaints from the API)
    assert table.all(view="view") == [rec]
    assert table.all(max_records=1) == [rec]
    assert table.all(page_size=1) == [rec]
    assert table.all(offset="") == [rec]
    assert table.all(fields=[cols.TEXT, cols.NUM]) == [rec]
    assert table.all(cell_format="json") == [rec]
    assert table.all(sort=[cols.TEXT, cols.NUM]) == [rec]
    assert table.all(time_zone="utc") == [rec]
    assert table.all(user_locale="en-ie") == [rec]
    assert table.all(return_fields_by_field_id=True) == [
        {
            "id": rec["id"],
            "createdTime": rec["createdTime"],
            "fields": {cols.TEXT_ID: rec["fields"][cols.TEXT]},
        }
    ]

    # Test that each supported parameter works with a POST
    # (or, at least, that we don't get complaints from the API)
    formula = f"{cols.TEXT} != '{'x' * 17000}'"
    assert table.all(formula=formula, view="view") == [rec]
    assert table.all(formula=formula, max_records=1) == [rec]
    assert table.all(formula=formula, page_size=1) == [rec]
    assert table.all(formula=formula, offset="") == [rec]
    assert table.all(formula=formula, fields=[cols.TEXT, cols.NUM]) == [rec]
    assert table.all(formula=formula, cell_format="json") == [rec]
    assert table.all(formula=formula, sort=[cols.TEXT, cols.NUM]) == [rec]
    assert table.all(formula=formula, time_zone="utc") == [rec]
    assert table.all(formula=formula, user_locale="en-ie") == [rec]
    assert table.all(formula=formula, return_fields_by_field_id=True) == [
        {
            "id": rec["id"],
            "createdTime": rec["createdTime"],
            "fields": {cols.TEXT_ID: rec["fields"][cols.TEXT]},
        }
    ]


def test_integration_field_equals(table: Table, cols):
    TEXT_VALUE = "Test {}".format(uuid4())
    NUM_VALUE = 12345
    values = {cols.TEXT: TEXT_VALUE, cols.NUM: NUM_VALUE}
    rv_create = table.create(values)

    # match all - finds
    rv_first = table.first(formula=fo.match(values))
    assert rv_first and rv_first["id"] == rv_create["id"]

    # match all - does not find
    values = {cols.TEXT: TEXT_VALUE, cols.NUM: 0}
    rv_first = table.first(formula=fo.match(values))
    assert rv_first is None

    # match all w/ match_any=True - does not find
    values = {cols.TEXT: TEXT_VALUE, cols.NUM: 0}
    rv_first = table.first(formula=fo.match(values, match_any=True))
    assert rv_first and rv_first["id"] == rv_create["id"]


def test_batch_upsert(table: Table, cols):
    one, two = table.batch_create(
        [
            {cols.TEXT: "One"},
            {cols.TEXT: "Two"},
        ]
    )

    # Test batch_upsert where replace=False
    result = table.batch_upsert(
        [
            {"id": one["id"], "fields": {cols.NUM: 3}},  # use id
            {"fields": {cols.TEXT: "Two", cols.NUM: 4}},  # use key_fields
            {"fields": {cols.TEXT: "Three", cols.NUM: 5}},  # create record
        ],
        key_fields=[cols.TEXT],
    )
    assert set(result["updatedRecords"]) == {one["id"], two["id"]}
    assert len(result["createdRecords"]) == 1
    assert len(result["records"]) == 3
    assert result["records"][0]["id"] == one["id"]
    assert result["records"][0]["fields"] == {cols.TEXT: "One", cols.NUM: 3}
    assert result["records"][1]["id"] == two["id"]
    assert result["records"][1]["fields"] == {cols.TEXT: "Two", cols.NUM: 4}
    assert result["records"][2]["fields"] == {cols.TEXT: "Three", cols.NUM: 5}

    # Test batch_upsert where replace=True
    result = table.batch_upsert(
        [
            {"id": one["id"], "fields": {cols.NUM: 3}},  # removes cols.TEXT
            {"fields": {cols.TEXT: "Two"}},  # removes cols.NUM
            {"fields": {cols.TEXT: "Three", cols.NUM: 6}},  # replaces cols.NUM
            {"fields": {cols.TEXT: None, cols.NUM: 7}},  # creates a record
        ],
        key_fields=[cols.TEXT],
        replace=True,
    )
    assert len(result["records"]) == 4
    assert result["records"][0]["id"] == one["id"]
    assert result["records"][0]["fields"] == {cols.NUM: 3}
    assert result["records"][1]["id"] == two["id"]
    assert result["records"][1]["fields"] == {cols.TEXT: "Two"}
    assert result["records"][2]["fields"] == {cols.TEXT: "Three", cols.NUM: 6}
    assert result["records"][3]["fields"] == {cols.NUM: 7}

    # Test that batch_upsert passes along return_fields_by_field_id
    result = table.batch_upsert(
        [{"fields": {cols.TEXT: "Two", cols.NUM: 8}}],
        key_fields=[cols.TEXT],
        return_fields_by_field_id=True,
    )
    assert result["records"] == [
        {
            "id": two["id"],
            "createdTime": two["createdTime"],
            "fields": {cols.TEXT_ID: "Two", cols.NUM_ID: 8},
        }
    ]


def test_integration_formula_datetime(table: Table, cols):
    VALUE = datetime.utcnow()
    str_value = fo.to_airtable_value(VALUE)
    rv_create = table.create({cols.DATETIME: str_value})
    rv_first = table.first(formula=fo.match({cols.DATETIME: str_value}))
    assert rv_first and rv_first["id"] == rv_create["id"]


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


def test_integration_field_equals_with_quotes(table: Table, cols):
    VALUE = "Contact's Name {}".format(uuid4())
    rv_create = table.create({cols.TEXT: VALUE})
    rv_first = table.first(formula=fo.match({cols.TEXT: VALUE}))
    assert rv_first and rv_first["id"] == rv_create["id"]

    VALUE = 'Some "Quote"  {}'.format(uuid4())
    rv_create = table.create({cols.TEXT: VALUE})
    rv_first = table.first(formula=fo.match({cols.TEXT: VALUE}))
    assert rv_first and rv_first["id"] == rv_create["id"]


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


def test_integration_attachment(table, cols, valid_img_url):
    rec = table.create({cols.ATTACHMENT: [attachment(valid_img_url)]})
    rv_get = table.get(rec["id"])
    assert rv_get["fields"]["attachment"][0]["filename"] == "logo.png"


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


def test_integration_comments(api, table: Table, cols):
    # Test that we can create a comment
    record = table.create({cols.TEXT: "Text"})
    whoami = api.whoami()["id"]
    table.add_comment(record["id"], f"A comment from @[{whoami}]")

    # Retrieve the comment we just created, make some assertions about its state
    comments = table.comments(record["id"])
    assert len(comments) == 1
    assert whoami in comments[0].text
    assert comments[0].author.id == whoami
    assert comments[0].mentioned[whoami].id == whoami

    # Test that we can modify the comment and examine its updated state
    comments[0].text = "Never mind!"
    comments[0].save()
    assert whoami not in comments[0].text
    assert comments[0].mentioned is None

    # Test that we can delete the comment
    comments[0].delete()
