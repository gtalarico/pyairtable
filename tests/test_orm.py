from datetime import datetime
from unittest import mock

import pytest
from requests_mock import Mocker

from pyairtable import Table
from pyairtable.orm import Model
from pyairtable.orm import fields as f
from pyairtable.testing import fake_meta, fake_record


def test_model_missing_meta():
    with pytest.raises(ValueError):

        class Address(Model):
            street = f.TextField("Street")

            class Meta:
                base_id = "required"
                table_name = "required"
                # api_key = "required"


def test_model_overlapping():
    # Should raise error because conflicts with .exists()
    with pytest.raises(ValueError):

        class Address(Model):
            Meta = fake_meta()
            exists = f.TextField("Exists")  # clases with Model.exists()


def test_model():
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
        link = f.LinkField("Link", Address, lazy=True)
        birthday = f.DateField("Birthday")

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


def test_from_record():
    class Contact(Model):
        Meta = fake_meta()
        first_name = f.TextField("First Name")
        timestamp = f.DatetimeField("Timestamp")

    # Fetch = True
    with mock.patch.object(Table, "get") as m_get:
        m_get.return_value = {
            "id": "recwnBLPIeQJoYVt4",
            "createdTime": "",
            "fields": {"First Name": "X", "Timestamp": "2014-09-05T12:34:56.000Z"},
        }
        contact = Contact.from_id("recwnBLPIeQJoYVt4")
        assert m_get.called

    assert m_get.called
    assert contact.id == "recwnBLPIeQJoYVt4"
    assert contact.first_name == "X"
    assert contact.timestamp.year == 2014

    # Fetch = False
    with mock.patch.object(Table, "get") as m_get_no_fetch:
        contact = Contact.from_id("recwnBLPIeQJoYVt4", fetch=False)
        assert not m_get_no_fetch.called
        assert not contact.first_name == "X"


def test_linked_record():
    class Address(Model):
        Meta = fake_meta(table_name="Address")
        street = f.TextField("Street")

    class Contact(Model):
        Meta = fake_meta(table_name="Contact")
        address = f.LinkField("Link", Address, lazy=True)

    record = {"id": "recFake", "createdTime": "", "fields": {"Street": "A"}}
    address = Address.from_id("recFake", fetch=False)

    # Id Reference
    contact = Contact(address=[address])
    assert contact.address[0].id == address.id
    assert not contact.address[0].street

    with Mocker() as mock:
        url = address.get_table().get_record_url(address.id)
        mock.get(url, status_code=200, json=record)
        contact.address[0].fetch()

    assert contact.address[0].street == "A"


def test_undeclared_field__from_id(requests_mock):
    """
    Test that Model.from_id ignores any fields which are missing from the Model definition.
    See https://github.com/gtalarico/pyairtable/issues/190
    """

    class JustName(Model):
        Meta = fake_meta()
        name = f.TextField("Name")

    record = fake_record({"Name": "Alice", "Address": "123 Fake St"})
    requests_mock.get(
        JustName.get_table().get_record_url(record["id"]),
        status_code=200,
        json=record,
    )

    instance = JustName.from_id(record["id"])
    assert instance.to_record()["fields"] == {"Name": "Alice"}


def test_undeclared_field__all():
    """
    Test that Model.all ignores any fields which are missing from the Model definition.
    """
    pytest.skip("To be implemented in 2.0.0; see #249")  # TODO


def test_undeclared_field__first():
    """
    Test that Model.first ignores any fields which are missing from the Model definition.
    """
    pytest.skip("To be implemented in 2.0.0; see #249")  # TODO
