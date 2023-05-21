from pyairtable import Base, Table


def test_repr(base):
    assert "Base" in base.__repr__()


def test_get_table(base: Base):
    rv = base.table("tablename")
    assert isinstance(rv, Table)
    assert rv.base == base
    assert rv.name == "tablename"
    assert rv.url == f"https://api.airtable.com/v0/{base.id}/tablename"
