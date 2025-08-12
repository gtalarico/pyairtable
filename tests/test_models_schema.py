from operator import attrgetter
from typing import List, Optional

import mock
import pytest

from pyairtable.models import schema
from pyairtable.models._base import AirtableModel
from pyairtable.testing import fake_id


@pytest.fixture
def mock_base_metadata(base, sample_json, requests_mock):
    base_json = sample_json("BaseCollaborators")
    requests_mock.get(base.urls.meta, json=base_json)
    requests_mock.get(base.urls.tables, json=sample_json("BaseSchema"))
    requests_mock.get(base.urls.shares, json=sample_json("BaseShares"))
    for pbd_id, pbd_json in base_json["interfaces"].items():
        requests_mock.get(base.urls.interface(pbd_id), json=pbd_json)


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
    cls = attrgetter(clsname)(schema)
    cls.model_validate(sample_json(clsname))


@pytest.mark.parametrize("cls", schema.FieldSchema.__args__)
def test_parse_field(sample_json, cls):
    cls.model_validate(sample_json("field_schema/" + cls.__name__))


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
    cls = attrgetter(clsname)(schema)
    obj = cls.model_validate(sample_json(clsname))
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
        "WorkspaceCollaborators.invite_links.via_base[0].id": "invJiqaXmPqqAPP99",
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
        return schema._find(self.inners, id_or_name)


def test_find():
    """
    Test that _find() retrieves an object based on ID or name,
    and skips any models that are marked as deleted.
    """

    collection = Outer.model_validate(
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
    method = getattr(base.collaborators(), f"add_{kind}")
    m = requests_mock.post(base.urls.collaborators, body="")
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
    requests_mock.get(workspace.urls.meta, json=workspace_json)
    method = getattr(workspace.collaborators(), f"add_{kind}")
    m = requests_mock.post(workspace.urls.collaborators, body="")
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


def test_invite_link__delete(
    base,
    workspace,
    requests_mock,
    mock_base_metadata,
    mock_workspace_metadata,
):
    """
    Test that we can revoke an invite link.
    """
    for invite_link in [
        base.collaborators().invite_links.via_base[0],
        base.collaborators().invite_links.via_workspace[0],
        base.collaborators().interfaces["pbdLkNDICXNqxSDhG"].invite_links[0],
        workspace.collaborators().invite_links.via_base[0],
        workspace.collaborators().invite_links.via_workspace[0],
    ]:
        endpoint = requests_mock.delete(invite_link._url)
        invite_link.delete()
        assert endpoint.call_count == 1


@pytest.fixture
def interface_url(base):
    return base.urls.interface("pbdLkNDICXNqxSDhG")


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
    requests_mock,  # unused; ensures no network traffic
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
    requests_mock,  # unused; ensures no network traffic
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


@pytest.mark.parametrize(
    "expr,expected_url",
    [
        (
            "base.collaborators()",
            "meta/bases/appLkNDICXNqxSDhG",
        ),
        (
            "base.collaborators().interfaces['pbdLkNDICXNqxSDhG']",
            "meta/bases/appLkNDICXNqxSDhG/interfaces/pbdLkNDICXNqxSDhG",
        ),
        (
            "base.collaborators().invite_links.via_base[0]",
            "meta/bases/appLkNDICXNqxSDhG/invites/invJiqaXmPqq6Ec87",
        ),
        (
            "base.collaborators().invite_links.via_workspace[0]",
            "meta/workspaces/wspmhESAta6clCCwF/invites/invJiqaXmPqq6Ec99",
        ),
        (
            "base.collaborators().interfaces['pbdLkNDICXNqxSDhG'].invite_links[0]",
            "meta/bases/appLkNDICXNqxSDhG/interfaces/pbdLkNDICXNqxSDhG/invites/invJiqaXmPqq6ABCD",
        ),
        (
            "workspace.collaborators().invite_links.via_base[0]",
            "meta/bases/appLkNDICXNqxSDhG/invites/invJiqaXmPqqAPP99",
        ),
        (
            "workspace.collaborators().invite_links.via_workspace[0]",
            "meta/workspaces/wspmhESAta6clCCwF/invites/invJiqaXmPqqWSP00",
        ),
        (
            "table.schema()",
            "meta/bases/appLkNDICXNqxSDhG/tables/tbltp8DGLhqbUmjK1",
        ),
        (
            "table.schema().field('fld1VnoyuotSTyxW1')",
            "meta/bases/appLkNDICXNqxSDhG/tables/tbltp8DGLhqbUmjK1/fields/fld1VnoyuotSTyxW1",
        ),
        (
            "table.schema().view('viwQpsuEDqHFqegkp')",
            "meta/bases/appLkNDICXNqxSDhG/views/viwQpsuEDqHFqegkp",
        ),
    ],
)
def test_restful_urls(
    expr,
    expected_url,
    api,
    base,
    workspace,
    mock_base_metadata,  # unused; ensures no network traffic
    mock_workspace_metadata,  # unused; ensures no network traffic
):
    """
    Test that the URLs for RestfulModels are generated correctly.
    """
    table = base.table("tbltp8DGLhqbUmjK1")
    obj = eval(expr, None, {"base": base, "table": table, "workspace": workspace})
    assert obj._url == api.build_url(expected_url)


@pytest.fixture
def base_share(base, mock_base_metadata) -> schema.BaseShares.Info:
    return base.shares()[0]


def test_share__enable(base_share, requests_mock):
    m = requests_mock.patch(base_share._url)
    base_share.enable()
    assert m.call_count == 1
    assert m.last_request.json() == {"state": "enabled"}


def test_share__disable(base_share, requests_mock):
    m = requests_mock.patch(base_share._url)
    base_share.disable()
    assert m.call_count == 1
    assert m.last_request.json() == {"state": "disabled"}


def test_share__delete(base_share, requests_mock):
    m = requests_mock.delete(base_share._url)
    base_share.delete()
    assert m.call_count == 1
    assert m.last_request.body is None


def test_workspace_restrictions(workspace, mock_workspace_metadata, requests_mock):
    restrictions = workspace.collaborators().restrictions
    restrictions.invite_creation = "unrestricted"
    restrictions.share_creation = "onlyOwners"

    m = requests_mock.post(restrictions._url)
    restrictions.save()
    assert m.call_count == 1
    assert m.last_request.json() == {
        "inviteCreationRestriction": "unrestricted",
        "shareCreationRestriction": "onlyOwners",
    }


def test_save_date_dependency_settings(api, base, requests_mock):
    table_id = fake_id("tbl")

    from pyairtable import orm

    class TaskModel(orm.Model):
        # Used to test that add_date_dependency accepts an ORM field.
        class Meta:
            api_key = api.api_key
            base_id = base.id
            table_name = "Tasks"

        duration = orm.fields.IntegerField("Duration")

    obj = {
        "id": table_id,
        "name": "Tasks",
        "description": "",
        "primaryFieldId": "fldName",
        "views": [],
        "fields": [
            {
                "id": "fldName",
                "name": "Name",
                "type": "singleLineText",
                "options": {},
            },
            {
                "id": "fldDepends",
                "name": "Depends",
                "type": "multipleRecordLinks",
                "options": {
                    "isReversed": False,
                    "linkedTableId": table_id,
                    "prefersSingleRecordLink": False,
                    "inverseLinkFieldId": None,
                    "viewIdForRecordSelection": None,
                },
            },
            {
                "id": "fldStartDate",
                "name": "Start Date",
                "type": "date",
                "options": {},
            },
            {
                "id": "fldEndDate",
                "name": "End Date",
                "type": "date",
                "options": {},
            },
            {
                "id": "fldDuration",
                "name": "Duration",
                "type": "number",
                "options": {},
            },
        ],
    }
    table_schema = schema.TableSchema.from_api(obj, api, context={"base": base})
    m = requests_mock.patch(table_schema._url, json=obj)
    table_schema.set_date_dependency(
        start_date_field="fldStartDate",
        end_date_field="End Date",
        duration_field=TaskModel.duration,
        rescheduling_mode="none",
    )
    assert m.call_count == 0

    table_schema.save()
    assert m.call_count == 1
    assert m.last_request.json() == {
        "name": "Tasks",
        "description": "",
        "dateDependencySettings": {
            "startDateFieldId": "fldStartDate",
            "endDateFieldId": "fldEndDate",
            "durationFieldId": "fldDuration",
            "reschedulingMode": "none",
            "isEnabled": True,
            "shouldSkipWeekendsAndHolidays": False,
            "holidays": [],
        },
    }


def test_save_date_dependency_settings__invalid_field(table_schema):
    with pytest.raises(KeyError, match=r"^'invalid_field'$"):
        table_schema.set_date_dependency(
            start_date_field="Name",
            end_date_field="Name",
            duration_field="Name",
            predecessor_field="invalid_field",
            rescheduling_mode="none",
        )
