import datetime

import pytest

from pyairtable.orm import fields as f
from pyairtable.orm.model import Model
from tests.test_orm import fake_meta


def fake_record(fields=None, **other_fields):
    return {
        "id": "recFakeTestingRec",
        "createdTime": datetime.datetime.now().isoformat(),
        "fields": {**(fields or {}), **other_fields},
    }


def test_field():
    class T:
        name = f.Field("Name")

    t = T()
    t.name = "x"
    assert t.name == "x"
    assert t.__dict__["_fields"]["Name"] == "x"


@pytest.mark.parametrize(
    "value",
    [
        "Test",
        1,
        1.5,
        True,
        datetime.date.today(),
        datetime.datetime.now(),
        list(),
        dict(),
    ],
    ids=type,
)
@pytest.mark.parametrize(
    "field_type",
    [
        f.TextField,
        f.EmailField,
        f.NumberField,
        f.IntegerField,
        f.FloatField,
        f.CheckboxField,
        f.DateField,
        f.DatetimeField,
    ],
)
def test_type_validation(field_type, value):
    """
    Test that attempting to assign the wrong type of value to a field
    will throw TypeError, but the right kind of value will work.
    """

    class T:
        the_field = field_type("Field Name")

    t = T()
    if isinstance(value, field_type.valid_types):
        t.the_field = value
    else:
        with pytest.raises(TypeError):
            t.the_field = value


@pytest.mark.parametrize(
    argnames=("field_type", "value"),
    argvalues=[
        (f.TextField, "name"),
        (f.EmailField, "x@y.com"),
        (f.NumberField, 1),
        (f.NumberField, 1.5),
        (f.IntegerField, 1),
        (f.FloatField, 1.5),
        (f.CheckboxField, True),
        (f.CheckboxField, False),
    ],
)
def test_value_preserved(field_type, value):
    """
    Test that the ORM does not modify values that can be persisted as-is.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = field_type("Field Name")

    new_obj = T()
    new_obj.the_field = value
    assert new_obj.to_record()["fields"] == {"Field Name": value}

    existing_obj = T.from_record(fake_record({"Field Name": value}))
    assert existing_obj.the_field == value


@pytest.mark.parametrize(
    argnames=("field_type", "api_value", "orm_value"),
    argvalues=[
        (f.DateField, "2023-01-01", datetime.date(2023, 1, 1)),
        (f.DatetimeField, "2023-04-12T09:30:00.000Z", datetime.datetime(2023, 4, 12, 9, 30, 0)),  # fmt: skip
    ],
)
def test_value_converted(field_type, api_value, orm_value):
    """
    Test that each ORM field type converts correctly in both directions.
    """

    class T(Model):
        Meta = fake_meta()
        the_field = field_type("Field Name")

    new_obj = T()
    new_obj.the_field = orm_value
    assert new_obj.to_record()["fields"] == {"Field Name": api_value}

    existing_obj = T.from_record(fake_record({"Field Name": api_value}))
    assert existing_obj.the_field == orm_value


@pytest.mark.skip("TODO")
def test_linked_field():
    ...


def test_datetime_field():
    class T:
        dt = f.DatetimeField("Datetime")

    field = T.__dict__["dt"]

    dt_str_from_airtable = "2000-01-02T03:04:05.000Z"
    rv_dt = field.to_internal_value(dt_str_from_airtable)
    rv_str = field.to_record_value(rv_dt)
    assert rv_str == dt_str_from_airtable

    assert (
        rv_dt.year == 2000
        and rv_dt.month == 1
        and rv_dt.day == 2
        and rv_dt.hour == 3
        and rv_dt.minute == 4
        and rv_dt.second == 5
    )


def test_date_field():
    class T:
        date = f.DateField("Date")

    field = T.__dict__["date"]

    date_str_from_airtable = "2000-01-02"
    rv_date = field.to_internal_value(date_str_from_airtable)
    rv_str = field.to_record_value(rv_date)
    assert rv_str == date_str_from_airtable

    assert rv_date.year == 2000 and rv_date.month == 1 and rv_date.day == 2


def test_lookup_field():
    class T:
        items = f.LookupField("Items")

    field = T.__dict__["items"]

    lookup_from_airtable = ["Item 1", "Item 2", "Item 3"]
    rv_list = field.to_internal_value(lookup_from_airtable)
    rv_json = field.to_record_value(rv_list)
    assert rv_json == lookup_from_airtable
    assert isinstance(rv_list, list)
    assert rv_list[0] == "Item 1" and rv_list[1] == "Item 2" and rv_list[2] == "Item 3"

    class T:
        events = f.LookupField("Event times", model=f.DatetimeField)

    field = T.__dict__["events"]

    lookup_from_airtable = [
        "2000-01-02T03:04:05.000Z",
        "2000-02-02T03:04:05.000Z",
        "2000-03-02T03:04:05.000Z",
    ]
    rv_to_internal = field.to_internal_value(lookup_from_airtable)
    rv_to_record = field.to_record_value(rv_to_internal)
    assert rv_to_record == lookup_from_airtable
    assert isinstance(rv_to_internal, list)
    assert (
        rv_to_internal[0] == "2000-01-02T03:04:05.000Z"
        and rv_to_internal[1] == "2000-02-02T03:04:05.000Z"
        and rv_to_internal[2] == "2000-03-02T03:04:05.000Z"
    )
