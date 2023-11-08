import datetime

import pytest
from requests import HTTPError

from pyairtable import Base, Table
from pyairtable.testing import fake_id


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


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        (
            dict(base_id="appFake"),
            "<Base id='appFake'>",
        ),
        (
            dict(base_id="appFake", name="Some name"),
            "<Base id='appFake' name='Some name'>",
        ),
        (
            dict(base_id="appFake", permission_level="editor"),
            "<Base id='appFake' permission_level='editor'>",
        ),
    ],
)
def test_repr(api, kwargs, expected):
    base = Base(api, **kwargs)
    assert repr(base) == expected


def test_url(base):
    assert base.url == "https://api.airtable.com/v0/appJMY16gZDQrMWpA"


def test_schema(base: Base, requests_mock, sample_json):
    m = requests_mock.get(base.meta_url("tables"), json=sample_json("BaseSchema"))
    table_schema = base.schema().table("tbltp8DGLhqbUmjK1")
    assert table_schema.name == "Apartments"
    assert m.call_count == 1

    # Test that we cache the result unless force=True
    base.schema()
    assert m.call_count == 1
    base.schema(force=True)
    assert m.call_count == 2


def test_table(base: Base, requests_mock):
    # no network traffic expected; requests_mock will fail if it happens
    rv = base.table("tablename")
    assert isinstance(rv, Table)
    assert rv.base == base
    assert rv.name == "tablename"
    assert rv.url == f"https://api.airtable.com/v0/{base.id}/tablename"


def test_table_validate(base: Base, requests_mock, sample_json):
    """
    Test that Base.table(..., validate=True) allows us to look up a table
    by either ID or name and get the correct properties.
    """
    m = requests_mock.get(base.meta_url("tables"), json=sample_json("BaseSchema"))
    base.table("tbltp8DGLhqbUmjK1", validate=True)
    base.table("Apartments", validate=True)
    assert m.call_count == 2
    # ...and will raise an exception if called with an invalid ID/name:
    with pytest.raises(KeyError):
        base.table("DoesNotExist", validate=True)


def test_tables(base: Base, requests_mock, sample_json):
    """
    Test that Base.tables() returns a list of validated Base instances.
    """
    requests_mock.get(base.meta_url("tables"), json=sample_json("BaseSchema"))
    result = base.tables()
    assert len(result) == 2
    assert result[0].name == "Apartments"
    assert result[1].name == "Districts"


def test_collaborators(base: Base, requests_mock, sample_json):
    requests_mock.get(base.meta_url(), json=sample_json("BaseCollaborators"))
    result = base.collaborators()
    assert result.individual_collaborators.via_base[0].email == "foo@bam.com"
    assert result.group_collaborators.via_workspace[0].group_id == "ugp1mKGb3KXUyQfOZ"


def test_shares(base: Base, requests_mock, sample_json):
    requests_mock.get(base.meta_url("shares"), json=sample_json("BaseShares"))
    result = base.shares()
    assert result[0].state == "enabled"
    assert result[1].effective_email_domain_allow_list == []


def test_webhooks(base: Base, requests_mock, sample_json):
    m = requests_mock.get(
        base.webhooks_url,
        json={"webhooks": [sample_json("Webhook")]},
    )
    webhooks = base.webhooks()
    assert m.call_count == 1
    assert len(webhooks) == 1
    assert webhooks[0].is_hook_enabled
    assert webhooks[0].last_notification_result.error


def test_webhook(base: Base, requests_mock, sample_json):
    requests_mock.get(base.webhooks_url, json={"webhooks": [sample_json("Webhook")]})
    webhook = base.webhook("ach00000000000001")
    assert webhook.id == "ach00000000000001"
    assert webhook.notification_url == "https://example.com/receive-ping"
    with pytest.raises(KeyError):
        base.webhook("DoesNotExist")


def test_add_webhook(base: Base, requests_mock):
    def _callback(request, context):
        expires = datetime.datetime.now() + datetime.timedelta(days=7)
        return {
            "id": fake_id("ach"),
            "expirationTime": expires.isoformat(),
            "macSecretBase64": "secret",
        }

    spec = {
        "options": {
            "filters": {
                "fromSources": ["client"],
                "dataTypes": ["tableData"],
                "recordChangeScope": "tbl00000000000000",
                "watchDataInFieldIds": [
                    "fld00000000000000",
                    "fld00000000000001",
                    "fld00000000000002",
                ],
            }
        }
    }
    m = requests_mock.post(base.webhooks_url, json=_callback)
    result = base.add_webhook("https://example.com/cb", spec)

    assert m.call_count == 1
    assert m.last_request.json()["notificationUrl"] == "https://example.com/cb"
    assert m.last_request.json()["specification"] == spec
    assert result.id.startswith("ach")
    assert result.mac_secret_base64 == "secret"


def test_name(api, base, requests_mock):
    """
    Test that Base().name is only set if passed explicitly to the constructor,
    or if it is available in cached schema information.
    """
    requests_mock.get(
        base.meta_url(),
        json={
            "id": base.id,
            "name": "Mocked Base Name",
            "permissionLevel": "create",
            "workspaceId": "wspFake",
        },
    )

    assert api.base(base.id).name is None
    assert base.name is None
    assert base.collaborators().name == "Mocked Base Name"
    assert base.name == "Mocked Base Name"

    # Test behavior with older constructor pattern
    with pytest.warns(DeprecationWarning):
        assert Base("tok", "app").name is None
    with pytest.warns(DeprecationWarning):
        assert Base("tok", "app", name="Base Name").name == "Base Name"


def test_create_table(base, requests_mock, sample_json):
    """
    Test that Base.create_table() makes two calls, one to create the table,
    and another to re-retrieve the entire base's schema.
    """
    schema = sample_json("BaseSchema")
    url = base.meta_url("tables")
    m = requests_mock.post(url, json={"id": "tbltp8DGLhqbUmjK1"})
    m_get = requests_mock.get(url + "?include=visibleFieldIds", json=schema)
    table = base.create_table(
        "Table Name", [{"name": "Whatever"}], description="Description"
    )
    assert isinstance(table, Table)
    assert m.call_count == m_get.call_count == 1
    assert m.request_history[-1].json() == {
        "name": "Table Name",
        "description": "Description",
        "fields": [{"name": "Whatever"}],
    }


def test_delete(base, requests_mock):
    """
    Test that Base.delete() hits the right endpoint.
    """
    m = requests_mock.delete(base.meta_url(), json={"id": base.id, "deleted": True})
    base.delete()
    assert m.call_count == 1


def test_delete__enterprise_only_table(api, base, requests_mock):
    """
    Test that Base.delete() explains why it might be getting a 404.
    """
    requests_mock.delete(base.meta_url(), status_code=404)
    with pytest.raises(HTTPError) as excinfo:
        base.delete()
    assert "Base.delete() requires an enterprise billing plan" in str(excinfo)
