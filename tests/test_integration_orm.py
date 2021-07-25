import pytest
import os
from airtable import Base, Table
from airtable.orm import Model
from airtable.orm import fields as f
from airtable.formulas import AND, EQUAL, FIELD

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

    yield _Address

    table = _Address.get_table()
    records = table.get_all()
    table.batch_delete([r["id"] for r in records])


@pytest.fixture
def Contact(Address):
    class _Contact(Model):
        first_name = f.TextField("First Name")
        last_name = f.TextField("Last Name")
        email = f.EmailField("Email")
        is_registered = f.CheckboxField("Registered")
        address = f.LinkField("Address", Address, lazy=True)

        class Meta:
            base_id = INTEGRATION_BASE
            api_key = API_KEY
            table_name = "Contact"

    yield _Contact

    table = _Contact.get_table()
    records = table.get_all()
    table.batch_delete([r["id"] for r in records])


@pytest.mark.integration
def test_integration_orm(Contact, Address):
    STREET = "123 Han"
    address = Address(street=STREET)
    address.save()

    contact = Contact(
        first_name="John",
        last_name="LastName",
        email="email@email.com",
        is_registered=True,
        address=[address.id],
    )

    assert contact.first_name == "John"
    assert contact.save()
    assert contact.id

    contact.first_name = "Not Gui"
    assert not contact.save()

    rv_address = contact.address
    assert rv_address.exists()

    assert rv_address.id == contact.address.id == address.id
    rv_address.reload()
    assert rv_address.street == contact.address.street == STREET
