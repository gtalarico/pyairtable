import pytest
from pyairtable.orm import fields as f


def test_field():
    class T:
        name = f.Field("Name")

    t = T()
    t.name = "x"
    assert t.name == "x"
    assert t.__dict__["_fields"]["Name"] == "x"


def test_field_types():
    class T:
        name = f.TextField("Name")
        check = f.CheckboxField("Check")
        email = f.EmailField("Email")

    t = T()
    t.name = "name"
    t.check = True
    t.email = "x@x.com"
    assert t.name == "name"
    assert t.check is True
    assert t.email == "x@x.com"


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
