from unittest import mock

from pyairtable import Api, Base, Table
from pyairtable.api.abstract import ApiAbstract


def test_repr(api):
    assert "Api" in api.__repr__()


def test_record_url(api: Api):
    rv = api.get_record_url("baseid", "tablename", "rec")
    assert rv == ApiAbstract("x")._get_record_url("baseid", "tablename", "rec")


def test_get_base(api: Api):
    rv = api.get_base("appTest")
    assert isinstance(rv, Base)
    assert rv.base_id == "appTest"
    assert rv.endpoint_url == api.endpoint_url


def test_get_table(api: Api):
    rv = api.get_table("appTest", "tblTest")
    assert isinstance(rv, Table)
    assert rv.base_id == "appTest"
    assert rv.table_name == "tblTest"
    assert rv.endpoint_url == api.endpoint_url
    assert rv.table_url == "https://api.airtable.com/v0/appTest/tblTest"


def test_default_endpoint_url(api: Api):
    rv = api.build_url("appTest", "tblTest")
    assert rv == "https://api.airtable.com/v0/appTest/tblTest"


def test_endpoint_url(api_with_endpoint_url: Api):
    rv = api_with_endpoint_url.build_url("appTest", "tblTest")
    assert rv == "https://api.example.com/v0/appTest/tblTest"


def test_endpoint_url_with_trailing_slash():
    api = Api("apikey", endpoint_url="https://api.example.com/")
    rv = api.build_url("appTest", "tblTest")
    assert rv == "https://api.example.com/v0/appTest/tblTest"


@mock.patch.object(ApiAbstract, "_get_record")
def test_get(m, api: Api, mock_response_single):
    m.return_value = mock_response_single
    rv = api.get("x", "y", "rec")
    assert rv == mock_response_single


@mock.patch.object(ApiAbstract, "_first")
def test_first(m, api: Api, mock_response_single):
    m.return_value = mock_response_single
    rv = api.first("x", "y")
    assert rv == mock_response_single


@mock.patch.object(ApiAbstract, "_all")
def test_all(m, api: Api, mock_response_list):
    m.return_value = mock_response_list
    rv = api.all("x", "y")
    assert rv == mock_response_list


@mock.patch.object(ApiAbstract, "_update")
def test_update(m, api: Api, mock_response_single):
    m.return_value = mock_response_single
    rv = api.update("x", "y", "rec", {"test": "test"})
    assert rv == mock_response_single
    assert ("x", "y", "rec", {"test": "test"}) == m.call_args[0][:4]
