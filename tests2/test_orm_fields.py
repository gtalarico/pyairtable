from airtable.orm import Model
from airtable.orm import fields as f


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


def test_linked_field():
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
