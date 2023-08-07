import datetime

import pytest

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


def test_repr(base):
    assert "Base" in base.__repr__()


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


def test_table__with_validation(base: Base, requests_mock, sample_json):
    """
    Test that Base.table() behaves differently once we've loaded a schema.
    """
    requests_mock.get(base.meta_url("tables"), json=sample_json("BaseSchema"))
    base.schema()
    # once a schema has been loaded, Base.table() can reuse objects by ID or name
    assert base.table("tbltp8DGLhqbUmjK1") == base.table("Apartments")
    # ...and will raise an exception if called with an invalid ID/name:
    with pytest.raises(KeyError):
        base.table("DoesNotExist")


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


def test_name(base, requests_mock):
    """
    Test that Base().name is only set if passed explicitly to the constructor,
    or if retrieved by a call to Base().info()
    """
    assert base.name is None
    assert Base("token", "base_id").name is None
    assert Base("token", "base_id", name="Base Name").name == "Base Name"

    requests_mock.get(
        base.meta_url(),
        json={
            "id": base.id,
            "name": "Base Name",
            "permissionLevel": "create",
            "workspaceId": "wspFake",
        },
    )
    assert base.info().name == "Base Name"
    assert base.name == "Base Name"
