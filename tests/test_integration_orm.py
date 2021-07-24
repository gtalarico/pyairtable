import pytest
import os
from airtable import Base, Table
from airtable.orm import Model
from airtable.orm import fields as f
from airtable.formulas import AND, EQUAL, FIELD, STR_VALUE

INTEGRATION_BASE = "appaPqizdsNHDvlEm"
API_KEY = os.environ["AIRTABLE_API_KEY"]


@pytest.fixture
def Address():
    class _Address(Model):
        street = f.TextField("Street")

        class Meta:
            base_id = INTEGRATION_BASE
            api_key = API_KEY
            table_name = "Address"

    return _Address


@pytest.fixture
def Contact(Address):
    class _Contact(Model):
        first_name = f.TextField("First Name")
        last_name = f.TextField("Last Name")
        email = f.EmailField("Email")
        is_registered = f.CheckboxField("Registered")
        link = f.LinkField("Link", Address, lazy=True)

        class Meta:
            base_id = INTEGRATION_BASE
            api_key = API_KEY
            table_name = "Contact"

    return _Contact


@pytest.mark.integration
def test_integration_orm(Contact, Address):
    breakpoint()
    contact = Contact(
        first_name="Gui",
        last_name="Talarico",
        email="gui@gui.com",
        is_registered=True,
    )
    contact.first_name
    assert contact.first_name == "Gui"
    assert contact.save()
    assert contact.id
    contact.first_name = "Not Gui"
    assert not contact.save()
    # assert contact.delete()

    print(contact.to_record())
    print(Address().to_record())
    contact2 = Contact.from_id("recwnBLPIeQJoYVt4")
    print(Address().to_record())
    # assert contact2.id

    address = contact2.link
    assert address
    print(address.to_record())
    address.reload()
    print(address.to_record())
