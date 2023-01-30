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
    
    
def test_phone_field():
    class T:
        phone = f.PhoneField("Phone")
        
    field = T.__dict__["phone"]
    
    received_values = [
        '9876543210',
        '987-654-3210',
        '(987) 654-3210',
        '987 654 3210',
        '987.654.3210',
        '+1 987.654.3210',
        '+1 (987) 654.3210',
        '+19876543210',
    ]
    
    for value in received_values:
        t = T()
        t.phone = value
        
        rv_e164 = field.to_internal_value(value)
        rv_str = field.to_record_value(value)
        
        print(value)
        
        assert rv_e164 == '+19876543210'
        assert rv_str == '+1 987-654-3210'
        assert t.phone == '+1 987-654-3210'

    
def test_lookup_field():
    class T:
        items = f.LookupField("Items")
        
    field = T.__dict__["items"]
    
    lookup_from_airtable = ["Item 1", "Item 2", "Item 3"]
    rv_list = field.to_internal_value(lookup_from_airtable)
    rv_json = field.to_record_value(rv_list)
    assert rv_json == lookup_from_airtable
    assert isinstance(rv_list, list)
    assert (
        rv_list[0] == 'Item 1'
        and rv_list[1] == 'Item 2'
        and rv_list[2] == 'Item 3'
    )
    
    class T:
        events = f.LookupField("Event times", model=f.DatetimeField)
        
    field = T.__dict__["events"]
    
    lookup_from_airtable = ["2000-01-02T03:04:05.000Z", "2000-02-02T03:04:05.000Z", "2000-03-02T03:04:05.000Z"]
    rv_to_internal = field.to_internal_value(lookup_from_airtable)
    rv_to_record = field.to_record_value(rv_to_internal)
    assert rv_to_record == lookup_from_airtable
    assert isinstance(rv_to_internal, list)
    assert (
        rv_to_internal[0] == '2000-01-02T03:04:05.000Z'
        and rv_to_internal[1] == '2000-02-02T03:04:05.000Z'
        and rv_to_internal[2] == '2000-03-02T03:04:05.000Z'
    )
