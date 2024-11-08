from unittest import mock

import pytest

from pyairtable import Api, Base, Table  # noqa


@pytest.fixture
def mock_bases_endpoint(api, requests_mock, sample_json):
    return requests_mock.get(api.urls.bases, json=sample_json("Bases"))


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


@pytest.mark.parametrize("base_id", ("appLkNDICXNqxSDhG", "Apartment Hunting"))
def test_base(api, base_id, mock_bases_endpoint):
    # test behavior without validation
    base = api.base(base_id)
    assert base.id == base_id
    assert base.name is None
    assert base.permission_level is None
    assert mock_bases_endpoint.call_count == 0

    # test behavior with validation
    base = api.base(base_id, validate=True)
    assert base.id == "appLkNDICXNqxSDhG"
    assert base.name == "Apartment Hunting"
    assert base.permission_level == "create"
    assert mock_bases_endpoint.call_count == 1

    # calling a second time uses cached information...
    api.base(base_id, validate=True)
    assert mock_bases_endpoint.call_count == 1

    # ...unless we also pass force=True
    base = api.base(base_id, validate=True, force=True)
    assert mock_bases_endpoint.call_count == 2


def test_bases(api, mock_bases_endpoint):
    base_ids = [base.id for base in api.bases()]
    assert mock_bases_endpoint.call_count == 1
    assert base_ids == ["appLkNDICXNqxSDhG", "appSW9R5uCNmRmfl6"]

    # Should not make a second API call...
    assert [base.id for base in api.bases()] == base_ids
    assert mock_bases_endpoint.call_count == 1
    # ....unless we force it:
    reloaded = api.bases(force=True)
    assert [base.id for base in reloaded] == base_ids
    assert mock_bases_endpoint.call_count == 2


def test_iterate_requests(api: Api, requests_mock):
    url = "https://example.com"
    response_list = [{"json": {"page": n, "offset": n + 1}} for n in range(1, 3)]
    response_list[-1]["json"]["offset"] = None
    requests_mock.get(url, response_list=response_list)
    responses = list(api.iterate_requests("GET", url))
    assert responses == [response["json"] for response in response_list]


def test_iterate_requests__invalid_type(api: Api, requests_mock):
    url = "https://example.com"
    response_list = [{"json": {"page": n, "offset": n + 1}} for n in range(1, 3)]
    response_list.append({"json": "anything but a dict, and we stop immediately"})
    requests_mock.get(url, response_list=response_list)
    responses = list(api.iterate_requests("GET", url))
    assert responses == [response["json"] for response in response_list]


def test_workspace(api):
    assert api.workspace("wspFake").id == "wspFake"


def test_enterprise(api, requests_mock, sample_json):
    url = api.build_url("meta/enterpriseAccount/entUBq2RGdihxl3vU")
    requests_mock.get(url, json=sample_json("EnterpriseInfo"))
    enterprise = api.enterprise("entUBq2RGdihxl3vU")
    assert enterprise.id == "entUBq2RGdihxl3vU"


def test_create_base(api):
    """
    Test that Api.create_base is a passthrough to Workspace.create_base
    """
    with mock.patch("pyairtable.Workspace.create_base") as m:
        api.create_base("wspFake", "Fake Name", [])

    m.assert_called_once_with("Fake Name", [])
