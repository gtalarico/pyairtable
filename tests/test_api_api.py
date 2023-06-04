from pyairtable import Api, Base, Table  # noqa


def test_repr(api):
    assert "Api" in api.__repr__()


def test_get_base(api: Api):
    rv = api.base("appTest")
    assert isinstance(rv, Base)
    assert rv.id == "appTest"
    assert rv.api == api


def test_get_table(api: Api):
    rv = api.table("appTest", "tblTest")
    assert isinstance(rv, Table)
    assert rv.name == "tblTest"
    assert rv.base.id == "appTest"


def test_default_endpoint_url(api: Api):
    rv = api.build_url("appTest", "tblTest")
    assert rv == "https://api.airtable.com/v0/appTest/tblTest"


def test_endpoint_url():
    api = Api("apikey", endpoint_url="https://api.example.com")
    rv = api.build_url("appTest", "tblTest")
    assert rv == "https://api.example.com/v0/appTest/tblTest"


def test_endpoint_url_with_trailing_slash():
    api = Api("apikey", endpoint_url="https://api.example.com/")
    rv = api.build_url("appTest", "tblTest")
    assert rv == "https://api.example.com/v0/appTest/tblTest"


def test_update_api_key(api):
    """
    Test that changing the access token also changes the default request headers.
    """
    api.api_key = "123"
    assert "123" in api.session.headers["Authorization"]


def test_whoami(api, requests_mock):
    """
    Test the /whoami endpoint gets passed straight through.
    """
    payload = {
        "id": "usrFakeTestingUser",
        "scopes": [
            "data.records:read",
            "data.records:write",
        ],
    }
    requests_mock.get("https://api.airtable.com/v0/meta/whoami", json=payload)
    assert api.whoami() == payload
