from airtable.orm import Model
from airtable.orm import fields as f


class Address(Model):
    street = f.TextField("Street")

    class Meta:
        base_id = "x"
        api_key = "x"
        table_name = "x"


class Contact(Model):
    first_name = f.TextField("First Name")
    # address = f.LinkField("Address", "orm.Address")
    address = f.LinkField("Address", Address)

    class Meta:
        base_id = "x"
        api_key = "x"
        table_name = "x"


contact = Contact(address=[Address()])
ad = contact.address[0]
print(ad)
