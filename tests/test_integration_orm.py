import pytest
import os
from airtable import Base, Table
from airtable.orm import Model
from airtable.orm import fields as f
from airtable.formulas import AND, EQUAL, FIELD, STR_VALUE


@pytest.fixture
def Contact():
    class Address(Model):
        street = f.TextField("Street")

        class Meta:
            base_id = "required"
            table_name = "required"
            # api_key = "required"

    class Contact(Model):

        first_name = f.TextField("First Name")
        last_name = f.TextField("Last Name")
        email = f.EmailField("Email")
        is_registered = f.CheckboxField("Registered")
        link = f.LinkField("Link", Address, lazy=True)
        # link = f.MultiLinkField("Link", Address, lazy=True)

        class Meta:
            base_id = "appaPqizdsNHDvlEm"
            table_name = "Contact"
            api_key = os.environ["AIRTABLE_API_KEY"]

    return Contact


class TestOrm:
    def test_xxx(self):
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

        table = Table(base_id, "Contact", os.environ["AIRTABLE_API_KEY"])

        # formula = EQUAL("{First Name}", "'A'")
        # print(table.get_all(formula=formula))

        formula = AND(
            EQUAL(FIELD("First Name"), STR_VALUE("A")),
            EQUAL(FIELD("Last Name"), STR_VALUE("Talarico")),
            EQUAL(FIELD("Age"), STR_VALUE(15)),
        )
        print(table.get_all(formula=formula))
