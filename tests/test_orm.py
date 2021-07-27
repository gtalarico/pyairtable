from unittest import mock
from requests_mock import Mocker
import pytest
from airtable import Table
from airtable.orm import Model
from airtable.orm import fields as f


def test_model_missing_meta():
    class Address(Model):
        street = f.TextField("Street")

        class Meta:
            base_id = "required"
            table_name = "required"
            # api_key = "required"

    with pytest.raises(ValueError):
        Address()


def test_model():
    class Address(Model):
        street = f.TextField("Street")
        number = f.TextField("Number")

        class Meta:
            base_id = "address_base_id"
            table_name = "Address"
            api_key = "fake"

    class Contact(Model):

        first_name = f.TextField("First Name")
        last_name = f.TextField("Last Name")
        email = f.EmailField("Email")
        is_registered = f.CheckboxField("Registered")
        link = f.LinkField("Link", Address, lazy=True)

        class Meta:
            base_id = "contact_base_id"
            table_name = "Contact"
            api_key = "fake"

    contact = Contact(
        first_name="Gui", last_name="Talarico", email="gui@gui.com", is_registered=True
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

    # to_record (split)
    record = contact.to_record()
    assert record["id"] == contact.id
    assert record["createdTime"] == contact.created_time
    assert record["fields"]["First Name"] == contact.first_name


def test_from_record():
    class Contact(Model):

        first_name = f.TextField("First Name")

        class Meta:
            base_id = "contact_base_id"
            table_name = "Contact"
            api_key = "fake"

    with mock.patch.object(Table, "get") as m_get:
        m_get.return_value = {
            "id": "recwnBLPIeQJoYVt4",
            "createdTime": "",
            "fields": {"First Name": "X"},
        }
        contact = Contact.from_id("recwnBLPIeQJoYVt4")

    assert m_get.called
    assert contact.id == "recwnBLPIeQJoYVt4"
    assert contact.first_name == "X"


def test_linked_record():
    class Address(Model):
        street = f.TextField("Street")

        class Meta:
            base_id = "address_base_id"
            table_name = "Address"
            api_key = "fake"

    class Contact(Model):
        address = f.LinkField("Link", Address, lazy=True)

        class Meta:
            base_id = "contact_base_id"
            table_name = "Contact"
            api_key = "fake"

    record = {"id": "recFake", "createdTime": "", "fields": {"Street": "A"}}
    address = Address.from_id("recFake", fetch=False)

    # Id Reference
    contact = Contact(address=[address])
    assert contact.address[0].id == address.id
    assert not contact.address[0].street

    with Mocker() as mock:
        url = address.get_table().get_record_url(address.id)
        mock.get(url, status_code=200, json=record)
        contact.address[0].reload()

    assert contact.address[0].street == "A"