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


def test_get_table(base: Base):
    rv = base.table("tablename")
    assert isinstance(rv, Table)
    assert rv.base == base
    assert rv.name == "tablename"
    assert rv.url == f"https://api.airtable.com/v0/{base.id}/tablename"


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
