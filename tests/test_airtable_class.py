from posixpath import join as urljoin

import pytest
from requests_mock import Mocker
from six.moves.urllib.parse import urlencode

from airtable import Airtable


def test_repr(table):
    assert "<Airtable" in table.__repr__()


@pytest.mark.parametrize(
    "base_key,table_name,table_url_suffix",
    [
        ("abc", "My Table", "abc/My%20Table"),
        ("abc", "SomeTable", "abc/SomeTable"),
        ("abc", "Table-fake", "abc/Table-fake"),
    ],
)
def test_url(base_key, table_name, table_url_suffix):
    table = Airtable(base_key, table_name, api_key="x")
    assert table.url_table == "{0}/{1}".format(table.API_URL, table_url_suffix)


def test_record_url(table):
    rv = table.record_url("xxx")
    assert rv == urljoin(table.url_table, "xxx")


def test_get(table, mock_response_single):
    _id = mock_response_single["id"]
    with Mocker() as mock:
        mock.get(table.record_url(_id), status_code=200, json=mock_response_single)
        resp = table.get(_id)
    # assert sorted(resp.items()) == sorted(mock_response_single.items())
    assert dict_equals(resp, mock_response_single)


def test_get_all(table, mock_response_list, mock_records):
    with Mocker() as mock:
        mock.get(
            table.url_table,
            status_code=200,
            json=mock_response_list[0],
            complete_qs=True,
        )
        for n, resp in enumerate(mock_response_list, 1):
            offset = resp.get("offset", None)
            if not offset:
                continue
            offset_url = table.url_table + "?offset={}".format(offset)
            mock.get(
                offset_url,
                status_code=200,
                json=mock_response_list[1],
                complete_qs=True,
            )
        response = table.get_all()

    for n, resp in enumerate(response):
        # assert sorted(resp.items()) == sorted(mock_records[n].items())
        assert dict_equals(resp, mock_records[n])


def test_insert(table, mock_response_single):
    with Mocker() as mock:
        post_data = mock_response_single["fields"]
        mock.post(
            table.url_table,
            status_code=201,
            json=mock_response_single,
            additional_matcher=match_request_data(post_data),
        )
        resp = table.insert(post_data)
    assert dict_equals(resp, mock_response_single)


def test_match(table, mock_response_single):
    params = urlencode({"FilterByFormula": "{Value}='abc'"})
    print(table.url_table)
    print(params)
    with Mocker() as mock:
        mock.get(
            table.url_table + "?" + params,
            status_code=200,
            json={
                "records": [
                    mock_response_single,
                    mock_response_single
                ]
            },
        )
        resp = table.match("Value", "abc")
    assert resp == mock_response_single


def test_match_not_found(table, mock_response_single):
    params = urlencode({"FilterByFormula": "{Value}='abc'"})
    with Mocker() as mock:
        mock.get(
            table.url_table + "?" + params,
            status_code=200,
            json={"records": []}
        )
        resp = table.match("Value", "abc")
    assert resp == {}


@pytest.mark.skip("Todo")
def test_search(table, mock_response_single):
    pass


@pytest.mark.skip("Todo")
def test_batch_insert(table, mock_response_single):
    pass


@pytest.mark.skip("Todo")
def test_update(table, mock_response_single):
    pass


@pytest.mark.skip("Todo")
def test_replace(table, mock_response_single):
    pass


@pytest.mark.skip("Todo")
def test_replace_by_field(table, mock_response_single):
    pass


@pytest.mark.skip("Todo")
def test_delete_by_field(table, mock_response_single):
    pass


@pytest.mark.skip("Todo")
def test_batch_delete(table, mock_response_single):
    pass


# Helpers


def match_request_data(post_data):
    """ Custom Matches, check that provided Request data is correct"""

    def _match_request_data(request):
        request_data_fields = request.json()["fields"]
        return dict_equals(request_data_fields, post_data)

    return _match_request_data


def dict_equals(d1, d2):
    return sorted(d1.items()) == sorted(d2.items())
