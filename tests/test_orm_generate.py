import pytest

from pyairtable.models import schema
from pyairtable.orm import generate
from pyairtable.testing import fake_id


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Apartments", "Apartment"),
        ("Apartment", "Apartment"),
        ("Ice Cold Slushees", "IceColdSlushee"),
        ("Table 5.6", "Table5_6"),
        ("53rd Avenue", "_53rdAvenue"),
        ("(53rd Avenue)", "_53rdAvenue"),
    ],
)
def test_table_class_name(value, expected):
    assert generate.table_class_name(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Apartments", "apartments"),
        ("Apartment", "apartment"),
        ("Ice Cold Slushees", "ice_cold_slushees"),
        ("Checked?", "checked"),
        ("Is checked?", "is_checked"),
        ("* Something weird (but kinda long!)", "something_weird_but_kinda_long"),
        ("Section 5.6", "section_5_6"),
        ("53rd Avenue", "_53rd_avenue"),
        ("(53rd Avenue)", "_53rd_avenue"),
    ],
)
def test_field_variable_name(value, expected):
    assert generate.field_variable_name(value) == expected


@pytest.mark.parametrize(
    "result_schema,expected",
    [
        (None, "Any"),
        ({"type": "multipleRecordLinks"}, "str"),
        ({"type": "singleLineText"}, "str"),
        ({"type": "number"}, "Union[int, float]"),
        ({"type": "date"}, "date"),
        ({"type": "dateTime"}, "datetime"),
        ({"type": "rating"}, "int"),
        ({"type": "duration"}, "timedelta"),
        ({"type": "checkbox"}, "bool"),
        ({"type": "multipleAttachments"}, "dict"),
        ({"type": "multipleSelects"}, "str"),
    ],
)
def test_lookup_field_type_annotation(result_schema, expected):
    struct = {
        "id": fake_id("fld"),
        "name": "Fake Field",
        "type": "multipleLookupValues",
        "options": {"isValid": True, "result": result_schema},
    }
    obj = schema.MultipleLookupValuesFieldSchema.model_validate(struct)
    assert generate.lookup_field_type_annotation(obj) == expected


@pytest.mark.parametrize(
    "schema_data,expected",
    [
        # basic field is looked up from the type
        (
            {"type": "singleLineText"},
            "field = F.TextField('Field')",
        ),
        # formula field that's missing result.type gets a generic field
        (
            {"type": "formula", "options": {"formula": "1", "isValid": True}},
            "field = F.Field('Field', readonly=True)",
        ),
        # formula field with result.type should look up the right class
        (
            {
                "type": "formula",
                "options": {
                    "formula": "1",
                    "isValid": True,
                    "result": {"type": "multipleAttachments"},
                },
            },
            "field = F.AttachmentsField('Field', readonly=True)",
        ),
        # lookup field should share more about types
        (
            {
                "type": "multipleLookupValues",
                "options": {
                    "isValid": True,
                    "fieldIdInLinkedValue": fake_id("fld"),
                    "recordLinkFieldId": fake_id("fld"),
                    "result": {"type": "duration"},
                },
            },
            "field = F.LookupField[timedelta]('Field')",
        ),
    ],
)
def test_field_builder(schema_data, expected):
    schema_data = {"id": fake_id("fld"), "name": "Field", **schema_data}
    field_schema = schema.parse_field_schema(schema_data)
    builder = generate.FieldBuilder(field_schema, lookup={})
    assert str(builder) == expected


def test_generate(base, mock_base_metadata):
    builder = generate.ModelFileBuilder(base)
    code = str(builder)
    assert code == (
        """\
from __future__ import annotations

import os
from functools import partial

from pyairtable.orm import Model
from pyairtable.orm import fields as F


class Apartment(Model):
    class Meta:
        api_key = partial(os.environ.get, 'AIRTABLE_API_KEY')
        base_id = 'appLkNDICXNqxSDhG'
        table_name = 'Apartments'

    name = F.TextField('Name')
    pictures = F.AttachmentsField('Pictures')
    district = F.LinkField['District']('District', model='District')


class District(Model):
    class Meta:
        api_key = partial(os.environ.get, 'AIRTABLE_API_KEY')
        base_id = 'appLkNDICXNqxSDhG'
        table_name = 'Districts'

    name = F.TextField('Name')
    apartments = F.LinkField['Apartment']('Apartments', model='Apartment')


__all__ = [
    'Apartment',
    'District',
]"""
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"table_names": ["Apartments"]},
        {"table_ids": ["tbltp8DGLhqbUmjK1"]},
    ],
)
def test_generate__table_names(base, kwargs, mock_base_metadata):
    """
    Test that we can generate only some tables, and link fields
    will reflect the fact that some tables are not represented.
    """
    builder = generate.ModelFileBuilder(base, **kwargs)
    code = str(builder)
    assert code == (
        """\
from __future__ import annotations

import os
from functools import partial

from pyairtable.orm import Model
from pyairtable.orm import fields as F


class Apartment(Model):
    class Meta:
        api_key = partial(os.environ.get, 'AIRTABLE_API_KEY')
        base_id = 'appLkNDICXNqxSDhG'
        table_name = 'Apartments'

    name = F.TextField('Name')
    pictures = F.AttachmentsField('Pictures')
    district = F._ListField[str]('District')


__all__ = [
    'Apartment',
]"""
    )
