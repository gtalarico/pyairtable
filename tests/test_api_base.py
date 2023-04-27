from unittest import mock

from pyairtable import Base, Table
from pyairtable.api.abstract import ApiAbstract


def test_repr(base):
    assert "Base" in base.__repr__()


def test_record_url(base: Base):
    rv = base.get_record_url("tablename", "rec")
    assert rv == f"https://api.airtable.com/v0/{base.base_id}/tablename/rec"


def test_get_table(base: Base):
    rv = base.get_table("tablename")
    assert isinstance(rv, Table)
    assert rv.base_id == base.base_id
    assert rv.table_name == "tablename"
    assert rv.table_url == f"https://api.airtable.com/v0/{base.base_id}/tablename"


@mock.patch.object(ApiAbstract, "_get_record")
def test_get(m, base: Base, mock_response_single):
    m.return_value = mock_response_single
    rv = base.get("tablename", "rec")
    assert rv == mock_response_single


@mock.patch.object(ApiAbstract, "_first")
def test_first(m, base: Base, mock_response_single):
    m.return_value = mock_response_single
    rv = base.first("tablename")
    assert rv == mock_response_single


@mock.patch.object(ApiAbstract, "_all")
def test_all(m, base: Base, mock_response_list):
    m.return_value = mock_response_list
    rv = base.all("tablename")
    assert rv == mock_response_list


@mock.patch.object(ApiAbstract, "_update")
def test_update(m, base: Base, mock_response_single):
    m.return_value = mock_response_single
    rv = base.update("tablename", "rec", {"test": "test"})
    assert rv == mock_response_single
    assert {"test": "test"} in m.call_args[0][:4]
