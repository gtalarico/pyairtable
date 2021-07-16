from unittest import mock
from airtable import Table
from airtable.orm import Model
from airtable.orm import fields as f


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

    assert contact.first_name == "Gui"
    assert not contact.id

    with mock.patch.object(Table, "create") as m_save:
        m_save.return_value = {"id": "id", "createdTime": "time"}
        contact.save()

    assert m_save.called
    assert contact.id == "id"

    # print(contact.to_record())

    # print(Address().to_record())
    # contact2 = Contact.from_id("recwnBLPIeQJoYVt4")
    # print(Address().to_record())

    # a ssert contact2.id

    # address = contact2.link
    # print(address.to_record())
    # address.reload()
    # print(address.to_record())
