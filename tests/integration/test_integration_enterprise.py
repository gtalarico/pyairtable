import os
import uuid

import pytest
from requests import HTTPError

import pyairtable

pytestmark = [pytest.mark.integration]


@pytest.fixture
def enterprise(api):
    try:
        return api.enterprise(os.environ["AIRTABLE_ENTERPRISE_ID"])
    except KeyError:
        pytest.skip("test requires AIRTABLE_ENTERPRISE_ID")


@pytest.fixture
def workspace_id():
    return "wsp0HnyXmNnKzc5ng"


@pytest.fixture
def workspace(api: pyairtable.Api, workspace_id):
    return api.workspace(workspace_id)


@pytest.fixture(autouse=True)
def confirm_enterprise_plan(workspace: pyairtable.Workspace):
    try:
        workspace.collaborators()
    except HTTPError:
        pytest.skip("This test requires creator access to an enterprise workspace")


@pytest.fixture
def blank_base(workspace: pyairtable.Workspace):
    base = workspace.create_base(
        f"Test {uuid.uuid1().hex}",
        [{"name": "One", "fields": [{"type": "singleLineText", "name": "Label"}]}],
    )
    try:
        yield base
    finally:
        base.delete()


def test_user(enterprise: pyairtable.Enterprise):
    """
    Test that we can retrieve information about the current logged-in user.
    """
    user_id = enterprise.api.whoami()["id"]
    assert user_id == enterprise.user(user_id).id


def test_user__invalid(enterprise):
    with pytest.raises(HTTPError):
        enterprise.user("invalidUserId")


def test_users(enterprise: pyairtable.Enterprise):
    """
    Test that we can retrieve information about an enterprise
    and retrieve user information by ID or by email.
    """
    user_ids = enterprise.info().user_ids[:5]
    users_from_ids = enterprise.users(user_ids)
    assert {u.id for u in users_from_ids} == set(user_ids)
    users_from_emails = enterprise.users(u.email for u in users_from_ids)
    assert {u.id for u in users_from_emails} == set(user_ids)


def test_create_table(blank_base: pyairtable.Base):
    """
    Test that we can create a new table on an existing base.
    """
    table = blank_base.create_table("Two", [{"type": "singleLineText", "name": "Name"}])
    assert table.schema().field("Name").type == "singleLineText"


def test_update_table(blank_base: pyairtable.Base):
    """
    Test that we can modify a table's name and description.
    """
    new_name = f"Renamed {uuid.uuid1().hex[-6:]}"
    schema = blank_base.schema().tables[0]
    schema.name = new_name
    schema.save()
    assert blank_base.schema(force=True).tables[0].name == new_name
    schema.description = "Renamed"
    schema.save()
    assert blank_base.schema(force=True).tables[0].description == "Renamed"


def test_create_field(blank_base: pyairtable.Base):
    """
    Test that we can create a new field on an existing table.
    """
    table = blank_base.tables()[0]
    assert len(table.schema().fields) == 1
    fld = table.create_field(
        "Status",
        type="singleSelect",
        options={
            "choices": [
                {"name": "Todo"},
                {"name": "In Progress"},
                {"name": "Done"},
            ]
        },
    )
    # Ensure we don't need to reload the schema to see this new field
    assert table._schema.field(fld.id).name == "Status"


def test_update_field(blank_base: pyairtable.Base):
    """
    Test that we can modify a field's name and description.
    """

    def reload_field():
        return blank_base.schema(force=True).tables[0].fields[0]

    field = reload_field()

    new_name = f"Renamed {uuid.uuid1().hex[-6:]}"
    field.name = new_name
    field.save()
    assert reload_field().name == new_name

    field.description = "Renamed"
    field.save()
    assert reload_field().description == "Renamed"


def test_audit_log(api):
    """
    Test that we can call the audit log endpoint.
    """
    if "AIRTABLE_ENTERPRISE_ID" not in os.environ:
        return pytest.skip("test_audit_log requires AIRTABLE_ENTERPRISE_ID")

    enterprise = api.enterprise(os.environ["AIRTABLE_ENTERPRISE_ID"])
    for page in enterprise.audit_log(page_limit=1):
        for event in page.events:
            assert isinstance(event.action, str)
