from operator import attrgetter
from typing import Any, List, Optional

import mock
import pytest

import pyairtable.models.schema
from pyairtable.models._base import AirtableModel
from pyairtable.testing import fake_id


@pytest.fixture
def schema_obj(api, sample_json):
    """
    Test fixture that provides a callable function which retrieves
    an object generated from tests/sample_data, and optionally
    retrieves an attribute of that object.
    """

    def _get_schema_obj(name: str, *, context: Any = None) -> Any:
        obj_name, _, obj_path = name.partition(".")
        obj_data = sample_json(obj_name)
        obj_cls = getattr(pyairtable.models.schema, obj_name)

        if context:
            obj = obj_cls.from_api(obj_data, api, context=context)
        else:
            obj = obj_cls.parse_obj(obj_data)

        if obj_path:
            obj = eval(f"obj.{obj_path}", None, {"obj": obj})
        return obj

    return _get_schema_obj


@pytest.fixture
def mock_base_metadata(api, base, sample_json, requests_mock):
    base_json = sample_json("BaseCollaborators")
    requests_mock.get(base.meta_url(), json=base_json)
    for pbd_id, pbd_json in base_json["interfaces"].items():
        requests_mock.get(base.meta_url("interfaces", pbd_id), json=pbd_json)


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
    "obj_path, expected_value",
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
        "WorkspaceCollaborators.invite_links.via_base[0].id": "invJiqaXmPqq6Ec87",
    }.items(),
)
def test_deserialized_values(obj_path, expected_value, schema_obj):
    """
    Spot check that certain values get loaded correctly from JSON into Python.
    This is not intended to be comprehensive, just another chance to catch regressions.
    """
    assert schema_obj(obj_path) == expected_value


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


@pytest.mark.parametrize(
    "kind,id",
    [
        ("user", "usrsOEchC9xuwRgKk"),
        ("group", "ugpR8ZT9KtIgp8Bh3"),
    ],
)
def test_base_collaborators__add(
    base, kind, id, requests_mock, sample_json, mock_base_metadata
):
    """
    Test that we can call base.collaborators().add_{user,group}
    to grant access to the base.
    """
    m = requests_mock.post(base.meta_url("collaborators"), body="")
    method = getattr(base.collaborators(), f"add_{kind}")
    method(id, "read")
    assert m.call_count == 1
    assert m.last_request.json() == {
        "collaborators": [{kind: {"id": id}, "permissionLevel": "read"}]
    }


@pytest.mark.parametrize(
    "kind,id",
    [
        ("user", "usrsOEchC9xuwRgKk"),
        ("group", "ugpR8ZT9KtIgp8Bh3"),
    ],
)
def test_workspace_collaborators__add(api, kind, id, requests_mock, sample_json):
    """
    Test that we can call workspace.collaborators().add_{user,group}
    to grant access to the workspace.
    """
    workspace_json = sample_json("WorkspaceCollaborators")
    workspace = api.workspace(workspace_json["id"])
    requests_mock.get(workspace.url, json=workspace_json)
    m = requests_mock.post(f"{workspace.url}/collaborators", body="")
    method = getattr(workspace.collaborators(), f"add_{kind}")
    method(id, "read")
    assert m.call_count == 1
    assert m.last_request.json() == {
        "collaborators": [{kind: {"id": id}, "permissionLevel": "read"}]
    }


@pytest.mark.parametrize(
    "name,id",
    [
        ("base", "appLkNDICXNqxSDhG"),
        ("workspace", "wspmhESAta6clCCwF"),
    ],
)
def test_update_collaborator(api, name, id, requests_mock, sample_json):
    """
    Test that we can call collaborators().update() to change the permission level
    of a user or group on a base or workspace.
    """
    target = getattr(api, name)(id)
    grp = fake_id("grp")
    obj = sample_json(f"{name.capitalize()}Collaborators")
    requests_mock.get(api.build_url(f"meta/{name}s/{id}"), json=obj)
    m = requests_mock.patch(api.build_url(f"meta/{name}s/{id}/collaborators/{grp}"))
    target.collaborators().update(grp, "read")
    assert m.call_count == 1
    assert m.last_request.json() == {"permissionLevel": "read"}


@pytest.mark.parametrize(
    "name,id",
    [
        ("base", "appLkNDICXNqxSDhG"),
        ("workspace", "wspmhESAta6clCCwF"),
    ],
)
def test_remove_collaborator(api, name, id, requests_mock, sample_json):
    """
    Test that we can call collaborators().remove() to revoke permissions
    from a user or group to a base or workspace.
    """
    target = getattr(api, name)(id)
    grp = fake_id("grp")
    obj = sample_json(f"{name.capitalize()}Collaborators")
    requests_mock.get(api.build_url(f"meta/{name}s/{id}"), json=obj)
    m = requests_mock.delete(api.build_url(f"meta/{name}s/{id}/collaborators/{grp}"))
    target.collaborators().remove(grp)
    assert m.call_count == 1
    assert m.last_request.body is None


@pytest.mark.parametrize("kind", ["base", "workspace"])
@pytest.mark.parametrize("via", ["base", "workspace"])
def test_collaborators_invite_link__delete(
    api, kind, via, base, workspace, requests_mock, sample_json
):
    """
    Test that we can revoke an invite link against a base or a workspace
    if it comes from either base.collaborators() or workspace.collaborators()
    """
    # obj/kind => the object we're using to get invite links
    obj = locals()[kind]
    # via => the pathway through which the invite link was created
    via_id = locals()[via].id

    # ensure .collaborators() gets the right kind of data back
    requests_mock.get(
        api.build_url(f"meta/{kind}s/{obj.id}"),
        json=sample_json(f"{kind.capitalize()}Collaborators"),
    )
    invite_link = getattr(obj.collaborators().invite_links, f"via_{via}")[0]

    # construct the URL we expect InviteLink.delete() to call
    url = api.build_url(f"meta/{via}s/{via_id}/invites/{invite_link.id}")
    endpoint = requests_mock.delete(url)
    print(f"{kind=} {via=} {url=}")

    # test that it happens
    invite_link.delete()
    assert endpoint.call_count == 1
    assert endpoint.last_request.method == "DELETE"


@pytest.fixture
def interface_url(base):
    return base.meta_url("interfaces", "pbdLkNDICXNqxSDhG")


@pytest.mark.parametrize("kind", ("user", "group"))
def test_add_interface_collaborator(
    base, kind, requests_mock, interface_url, mock_base_metadata
):
    m = requests_mock.post(f"{interface_url}/collaborators", body="")
    interface_schema = base.collaborators().interfaces["pbdLkNDICXNqxSDhG"]
    method = getattr(interface_schema, f"add_{kind}")
    method("testObjectId", "read")
    assert m.call_count == 1
    assert m.last_request.json() == {
        "collaborators": [
            {
                kind: {"id": "testObjectId"},
                "permissionLevel": "read",
            }
        ]
    }


def test_update_interface_collaborator(
    base, interface_url, requests_mock, mock_base_metadata
):
    m = requests_mock.patch(f"{interface_url}/collaborators/testObjectId")
    interface_schema = base.collaborators().interfaces["pbdLkNDICXNqxSDhG"]
    interface_schema.update("testObjectId", "read")
    assert m.call_count == 1
    assert m.last_request.json() == {"permissionLevel": "read"}


def test_remove_interface_collaborator(
    base, interface_url, requests_mock, mock_base_metadata
):
    m = requests_mock.delete(f"{interface_url}/collaborators/testObjectId")
    interface_schema = base.collaborators().interfaces["pbdLkNDICXNqxSDhG"]
    interface_schema.remove("testObjectId")
    assert m.call_count == 1
    assert m.last_request.body is None


@pytest.mark.parametrize(
    "target_path",
    (
        "BaseCollaborators",
        "WorkspaceCollaborators",
        "BaseCollaborators.interfaces['pbdLkNDICXNqxSDhG']",
    ),
)
@pytest.mark.parametrize("kind", ("user", "group"))
def test_add_collaborator(
    target_path,
    kind,
    schema_obj,
    requests_mock,  # ensures no network traffic
):
    target = schema_obj(target_path)
    with mock.patch.object(target.__class__, "add_collaborators") as m:
        target.add(kind, "testId", "read")
        m.assert_called_once_with([{kind: {"id": "testId"}, "permissionLevel": "read"}])


@pytest.mark.parametrize(
    "target_path",
    (
        "BaseCollaborators",
        "WorkspaceCollaborators",
        "BaseCollaborators.interfaces['pbdLkNDICXNqxSDhG']",
    ),
)
def test_add_collaborator__invalid_kind(
    target_path,
    schema_obj,
    requests_mock,  # ensures no network traffic
):
    target = schema_obj(target_path)
    with mock.patch.object(target.__class__, "add_collaborators") as m:
        with pytest.raises(ValueError):
            target.add("asdf", "testId", "read")
        assert m.call_count == 0


@pytest.mark.parametrize(
    "target_path",
    (
        "BaseCollaborators",
        "WorkspaceCollaborators",
        "BaseCollaborators.interfaces['pbdLkNDICXNqxSDhG']",
    ),
)
def test_add_collaborators(
    target_path,
    schema_obj,
    base,
    workspace,
    requests_mock,
):
    target = schema_obj(target_path, context={"base": base, "workspace": workspace})
    requests_mock.get(target._url, json=target._raw)
    m = requests_mock.post(target._url + "/collaborators")
    target.add_collaborators([1, 2, 3, 4])
    assert m.call_count == 1
    assert m.last_request.json() == {"collaborators": [1, 2, 3, 4]}
