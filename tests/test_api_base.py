import pytest

from pyairtable import Base, Table


def test_constructor(api):
    base = Base(api, "base_id")
    assert base.api == api
    assert base.id == "base_id"


def test_deprecated_constructor():
    with pytest.warns(DeprecationWarning):
        base = Base("api_key", "base_id")

    assert base.api.api_key == "api_key"
    assert base.id == "base_id"


def test_invalid_constructor():
    """
    Test that we get a TypeError if passing invalid kwargs to Base.
    """
    with pytest.raises(TypeError):
        Base(api_key="api_key", base_id="base_id")
    with pytest.raises(TypeError):
        Base("api_key", "base_id", timeout=(1, 1))


def test_repr(base):
    assert "Base" in base.__repr__()


def test_get_table(base: Base):
    rv = base.table("tablename")
    assert isinstance(rv, Table)
    assert rv.base == base
    assert rv.name == "tablename"
    assert rv.url == f"https://api.airtable.com/v0/{base.id}/tablename"
