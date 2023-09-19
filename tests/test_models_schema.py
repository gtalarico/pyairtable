from operator import attrgetter

import pytest

import pyairtable.models.schema


@pytest.mark.parametrize(
    "clsname",
    [
        "Bases",
        "BaseInfo",
        "BaseSchema",
        "TableSchema",
        "ViewSchema",
    ],
)
def test_parse(sample_json, clsname):
    cls = attrgetter(clsname)(pyairtable.models.schema)
    cls.parse_obj(sample_json(clsname))


@pytest.mark.parametrize("cls", pyairtable.models.schema.FieldSchema.__args__)
def test_parse_field(sample_json, cls):
    cls.parse_obj(sample_json("field_schema/" + cls.__name__))


@pytest.mark.parametrize(
    "clsname,method,id_or_name",
    [
        ("Bases", "base", "appLkNDICXNqxSDhG"),
        ("Bases", "base", "Apartment Hunting"),
        ("BaseSchema", "table", "tbltp8DGLhqbUmjK1"),
        ("BaseSchema", "table", "Apartments"),
        ("TableSchema", "field", "fld1VnoyuotSTyxW1"),
        ("TableSchema", "field", "Name"),
        ("TableSchema", "view", "viwQpsuEDqHFqegkp"),
        ("TableSchema", "view", "Grid view"),
    ],
)
def test_find_in_collection(clsname, method, id_or_name, sample_json):
    cls = attrgetter(clsname)(pyairtable.models.schema)
    obj = cls.parse_obj(sample_json(clsname))
    assert getattr(obj, method)(id_or_name)
