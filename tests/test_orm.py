from datetime import datetime
from operator import itemgetter
from unittest import mock

import pytest
from requests_mock import Mocker

from pyairtable import Table
from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_meta, fake_record


def test_model_missing_meta():
    """
    Test that we throw an exception if Meta is missing.
    """
    with pytest.raises(AttributeError):

        class Address(Model):
            street = f.TextField("Street")


def test_model_missing_meta_attribute():
    """
    Test that we throw an exception if Meta is missing a required attribute.
    """
    with pytest.raises(ValueError):

        class Address(Model):
            street = f.TextField("Street")

            class Meta:
                base_id = "required"
                table_name = "required"
                # api_key = "required"


def test_model_empty_meta():
    """
    Test that we throw an exception when a required Meta attribute is None.
    """
    with pytest.raises(ValueError):

        class Address(Model):
            Meta = fake_meta(api_key=None)
            street = f.TextField("Street")


def test_model_overlapping():
    # Should raise error because conflicts with .exists()
    with pytest.raises(ValueError):

        class Address(Model):
            Meta = fake_meta()
            exists = f.TextField("Exists")  # clases with Model.exists()


class Address(Model):
    Meta = fake_meta(table_name="Address")
    street = f.TextField("Street")
    number = f.TextField("Number")


class Contact(Model):
    Meta = fake_meta(table_name="Contact")
    first_name = f.TextField("First Name")
    last_name = f.TextField("Last Name")
    email = f.EmailField("Email")
    is_registered = f.CheckboxField("Registered")
    address = f.LinkField("Link", Address, lazy=True)
    birthday = f.DateField("Birthday")
    created_at = f.CreatedTimeField("Created At")


def test_model():
    contact = Contact(
        first_name="Gui",
        last_name="Talarico",
        email="gui@gui.com",
        is_registered=True,
        birthday=datetime(2020, 12, 12).date(),
    )

    # attribute look up
    assert contact.first_name == "Gui"
    assert not contact.id

    # delete
    with mock.patch.object(Table, "create") as m_save:
        m_save.return_value = {"id": "id", "createdTime": "time"}
        contact.save()

    assert m_save.called
    assert contact.id == "id"

    # delete
    with mock.patch.object(Table, "delete") as m_delete:
        m_delete.return_value = {"deleted": True}
        contact.delete()

    assert m_delete.called

    record = contact.to_record()
    assert record["id"] == contact.id
    assert record["createdTime"] == contact.created_time
    assert record["fields"]["First Name"] == contact.first_name


def test_first():
    with mock.patch.object(Table, "first") as m_first:
        m_first.return_value = {
            "id": "recwnBLPIeQJoYVt4",
            "createdTime": "",
            "fields": {
                "First Name": "X",
                "Created At": "2014-09-05T12:34:56.000Z",
            },
        }
        contact = Contact.first()

    assert contact.first_name == "X"


def test_first_none():
    with mock.patch.object(Table, "first") as m_first:
        m_first.return_value = None
        contact = Contact.first()

    assert contact is None


def test_from_record():
    # Fetch = True
    with mock.patch.object(Table, "get") as m_get:
        m_get.return_value = {
            "id": "recwnBLPIeQJoYVt4",
            "createdTime": "",
            "fields": {"First Name": "X", "Created At": "2014-09-05T12:34:56.000Z"},
        }
        contact = Contact.from_id("recwnBLPIeQJoYVt4")

    assert m_get.called
    assert contact.id == "recwnBLPIeQJoYVt4"
    assert contact.first_name == "X"
    assert contact.created_at.year == 2014

    # Fetch = False
    with mock.patch.object(Table, "get") as m_get_no_fetch:
        contact = Contact.from_id("recwnBLPIeQJoYVt4", fetch=False)
        assert not m_get_no_fetch.called
        assert not contact.first_name == "X"


def test_readonly_field_not_saved():
    """
    Test that we do not attempt to save readonly fields to the API,
    but we can retrieve readonly fields and set them on instantiation.
    """

    record = {
        "id": "recwnBLPIeQJoYVt4",
        "createdTime": datetime.utcnow().isoformat(),
        "fields": {
            "Birthday": "1970-01-01",
            "Age": 57,
        },
    }

    contact = Contact.from_record(record)
    with mock.patch.object(Table, "update") as m_update:
        m_update.return_value = record
        contact.birthday = datetime(2000, 1, 1)
        contact.save()

    # We should not pass 'Age' to the API
    m_update.assert_called_once_with(
        contact.id, {"Birthday": "2000-01-01"}, typecast=True
    )


def test_linked_record():
    record = {"id": "recFake", "createdTime": "", "fields": {"Street": "A"}}
    address = Address.from_id("recFake", fetch=False)

    # Id Reference
    contact = Contact(address=[address])
    assert contact.address[0].id == address.id
    assert not contact.address[0].street

    with Mocker() as mock:
        url = Address.get_table().record_url(address.id)
        mock.get(url, status_code=200, json=record)
        contact.address[0].fetch()

    assert contact.address[0].street == "A"


@pytest.mark.parametrize(
    "test_case",
    [
        ("from_id", lambda cls, id: cls.from_id(id)),
        ("first", lambda cls, _: cls.first()),
        ("all", lambda cls, _: cls.all()[0]),
    ],
    ids=itemgetter(0),
)
def test_undeclared_field(requests_mock, test_case):
    """
    Test that Model methods which fetch data from the Airtable API will
    ignore any fields which are missing from the Model definition.

    See https://github.com/gtalarico/pyairtable/issues/190
    """

    record = fake_record(
        Number="123",
        Street="Fake St",
        City="Springfield",
        State="IL",
    )

    requests_mock.get(
        Address.get_table().url,
        status_code=200,
        json={"records": [record]},
    )
    requests_mock.get(
        Address.get_table().record_url(record["id"]),
        status_code=200,
        json=record,
    )

    _, get_model_instance = test_case
    instance = get_model_instance(Address, record["id"])
    assert instance.to_record()["fields"] == {"Number": "123", "Street": "Fake St"}
