from unittest import mock

from pyairtable.api.abstract import ApiAbstract
from pyairtable import Api, Table


def test_repr(api):
    assert "Api" in api.__repr__()


def test_record_url(api: Api):
    rv = api.get_record_url("baseid", "tablename", "rec")
    assert rv == ApiAbstract("x")._get_record_url("baseid", "tablename", "rec")


def test_get_table(api: Api):
    rv = api.get_table("x", "y")
    assert isinstance(rv, Table)
    assert rv.base_id == "x"
    assert rv.table_name == "y"


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
