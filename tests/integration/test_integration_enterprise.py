import uuid

import pytest
from requests import HTTPError

import pyairtable

pytestmark = [pytest.mark.integration]


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
