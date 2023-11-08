from operator import attrgetter, itemgetter
from typing import List, Optional

import pytest

import pyairtable.models.schema
from pyairtable.models._base import AirtableModel


@pytest.mark.parametrize(
    "clsname",
    [
        "Bases",
        "BaseCollaborators",
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


@pytest.mark.parametrize(
    "test_case",
    {
        "BaseCollaborators.individual_collaborators.via_base[0].permission_level": "create",
        "BaseCollaborators.individual_collaborators.via_base[0].user_id": "usrsOEchC9xuwRgKk",
        "BaseSchema.tables[0].fields[1].type": "multipleAttachments",
        "BaseSchema.tables[0].fields[2].options.inverse_link_field_id": "fldWnCJlo2z6ttT8Y",
        "BaseSchema.tables[0].name": "Apartments",
        "BaseSchema.tables[0].views[0].type": "grid",
        "BaseShares.shares[0].effective_email_domain_allow_list": ["foobar.com"],
        "BaseShares.shares[2].state": "disabled",
        "EnterpriseInfo.email_domains[0].email_domain": "foobar.com",
        "EnterpriseInfo.email_domains[0].is_sso_required": True,
        "UserGroup.collaborations.base_collaborations[0].base_id": "appLkNDICXNqxSDhG",
        "UserGroup.members[1].user_id": "usrsOEchC9xuwRgKk",
        "UserInfo.collaborations.interface_collaborations[0].interface_id": "pbdyGA3PsOziEHPDE",
        "UserInfo.is_sso_required": True,
        "UserInfo.is_two_factor_auth_enabled": False,
        "UserInfo.name": "foo baz",
        "WorkspaceCollaborators.base_ids": ["appLkNDICXNqxSDhG", "appSW9R5uCNmRmfl6"],
        "WorkspaceCollaborators.invite_links.base_invite_links[0].id": "invJiqaXmPqq6Ec87",
    }.items(),
    ids=itemgetter(0),
)
def test_deserialized_values(test_case, sample_json):
    """
    Spot check that certain values get loaded correctly from JSON into Python.
    This is not intended to be comprehensive, just another chance to catch regressions.
    """
    clsname_attr, expected = test_case
    clsname = clsname_attr.split(".")[0]
    cls = attrgetter(clsname)(pyairtable.models.schema)
    obj = cls.parse_obj(sample_json(clsname))
    val = eval(clsname_attr, None, {clsname: obj})
    assert val == expected


class Outer(AirtableModel):
    inners: List["Outer.Inner"]

    class Inner(AirtableModel):
        id: str
        name: str
        deleted: Optional[bool] = None

    def find(self, id_or_name):
        return pyairtable.models.schema._find(self.inners, id_or_name)


def test_find():
    """
    Test that _find() retrieves an object based on ID or name,
    and skips any models that are marked as deleted.
    """

    collection = Outer.parse_obj(
        {
            "inners": [
                {"id": "0001", "name": "One"},
                {"id": "0002", "name": "Two"},
                {"id": "0003", "name": "Three", "deleted": True},
            ]
        }
    )
    assert collection.find("0001").id == "0001"
    assert collection.find("Two").id == "0002"
    with pytest.raises(KeyError):
        collection.find("0003")
    with pytest.raises(KeyError):
        collection.find("0004")
