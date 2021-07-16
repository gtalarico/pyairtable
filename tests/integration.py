import os
from airtable import Base, Table

base_id = "appaPqizdsNHDvlEm"
table_name = "table"
table = Table(base_id, table_name, os.environ["AIRTABLE_API_KEY"])

print(table.first())
exit()

rec = table.create({"text": "A", "number": 1, "boolean": True})
assert table.get(rec["id"])

rv = table.update(rec["id"], {"text": "B"})
assert rv["fields"]["text"] == "B"
assert rv["fields"]["number"] == 1

rv = table.update(rec["id"], {"number": 2}, replace=True)
assert rv["fields"] == {"number": 2}

# Get all
assert table.get_all()

# Delete
assert table.delete(rec["id"])


# Batch Insert
records = table.batch_create(
    [{"text": "A", "number": 1, "boolean": True} for _ in range(15)]
)

# Batch Delete
records = table.batch_delete([r["id"] for r in records])
assert len(records) == 15


base = Base(base_id, os.environ["AIRTABLE_API_KEY"])

rec = base.create(table_name, {"text": "A", "number": 1, "boolean": True})
assert base.get(table_name, rec["id"])

rv = base.update(table_name, rec["id"], {"text": "B"})
assert rv["fields"]["text"] == "B"

rv = base.update(table_name, rec["id"], {"number": 2}, replace=True)
assert rv["fields"] == {"number": 2}

# Get all
assert base.get_all(table_name)

# Delete
assert base.delete(table_name, rec["id"])


# Batch Insert
records = base.batch_create(
    table_name, [{"text": "A", "number": 1, "boolean": True} for _ in range(15)]
)

# Batch Delete
records = base.batch_delete(table_name, [r["id"] for r in records])
assert len(records) == 15


from airtable.orm import Model
from airtable.orm import fields as f


class Address(Model):
    street = f.TextField("Street")
    number = f.TextField("Number")

    class Meta:
        base_id = "appaPqizdsNHDvlEm"
        table_name = "Address"
        api_key = os.environ["AIRTABLE_API_KEY"]


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


contact = Contact(
    first_name="Gui", last_name="Talarico", email="gui@gui.com", is_registered=True
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
print(address.to_record())
address.reload()
print(address.to_record())


from airtable.formulas import AND, EQUAL, FIELD, VALUE


table = Table(base_id, "Contact", os.environ["AIRTABLE_API_KEY"])

# formula = EQUAL("{First Name}", "'A'")
# print(table.get_all(formula=formula))

formula = AND(
    EQUAL(FIELD("First Name"), VALUE("A")),
    EQUAL(FIELD("Last Name"), VALUE("Talarico")),
    EQUAL(FIELD("Age"), VALUE(15)),
)
print(table.get_all(formula=formula))
