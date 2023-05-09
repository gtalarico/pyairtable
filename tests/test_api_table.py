from posixpath import join as urljoin

import pytest
from requests import Request
from requests_mock import Mocker

from pyairtable import Table


def test_repr(table):
    assert "<Table" in table.__repr__()


@pytest.mark.parametrize(
    "base_id,table_name,table_url_suffix",
    [
        ("abc", "My Table", "abc/My%20Table"),
        ("abc", "SomeTable", "abc/SomeTable"),
        ("abc", "Table-fake", "abc/Table-fake"),
    ],
)
def test_url(base_id, table_name, table_url_suffix):
    table = Table("apikey", base_id, table_name)
    assert table.table_url == f"https://api.airtable.com/v0/{table_url_suffix}"


def test_chunk(table):
    chunks = [chunk for chunk in table._chunk([0, 0, 1, 1, 2, 2, 3], 2)]
    assert chunks[0] == [0, 0]
    assert chunks[1] == [1, 1]
    assert chunks[2] == [2, 2]
    assert chunks[3] == [3]


def test_record_url(table):
    rv = table.get_record_url("xxx")
    assert rv == urljoin(table.table_url, "xxx")


def test_api_key(table, mock_response_single):
    def match_auth_header(request):
        expected_auth_header = "Bearer {}".format(table.api_key)
        return (
            "Authorization" in request.headers
            and request.headers["Authorization"] == expected_auth_header
        )

    with Mocker() as m:
        m.get(
            table.get_record_url("rec"),
            status_code=200,
            json=mock_response_single,
            additional_matcher=match_auth_header,
        )

        table.get("rec")


def test_update_api_key(table):
    table.api_key = "123"
    assert "123" in table.session.headers["Authorization"]


def test_get_base(table):
    base = table.get_base()
    assert base.base_id == table.base_id and base.api_key == table.api_key


def test_get(table, mock_response_single):
    _id = mock_response_single["id"]
    with Mocker() as mock:
        mock.get(table.get_record_url(_id), status_code=200, json=mock_response_single)
        resp = table.get(_id)
    assert dict_equals(resp, mock_response_single)


def test_first(table, mock_response_single):
    mock_response = {"records": [mock_response_single]}
    with Mocker() as mock:
        url = Request("get", table.table_url, params={"maxRecords": 1}).prepare().url
        mock.get(
            url,
            status_code=200,
            json=mock_response,
        )
        rv = table.first()
        assert rv
    assert rv["id"] == mock_response_single["id"]


def test_first_via_post(table, mock_response_single):
    mock_response = {"records": [mock_response_single]}
    with Mocker() as mock:
        url = table.table_url + "/listRecords"
        formula = f"RECORD_ID() != '{'x' * 17000}'"
        mock_endpoint = mock.post(url, status_code=200, json=mock_response)
        rv = table.first(formula=formula)

    assert mock_endpoint.last_request.json() == {
        "filterByFormula": formula,
        "maxRecords": 1,
        "pageSize": 1,
    }
    assert rv == mock_response_single


def test_first_none(table, mock_response_single):
    mock_response = {"records": []}
    with Mocker() as mock:
        url = Request("get", table.table_url, params={"maxRecords": 1}).prepare().url
        mock.get(
            url,
            status_code=200,
            json=mock_response,
        )
        rv = table.first()
        assert rv is None


def test_all(table, mock_response_list, mock_records):
    with Mocker() as mock:
        mock.get(
            table.table_url,
            status_code=200,
            json=mock_response_list[0],
            complete_qs=True,
        )
        for n, resp in enumerate(mock_response_list, 1):
            offset = resp.get("offset", None)
            if not offset:
                continue
            offset_url = table.table_url + "?offset={}".format(offset)
            mock.get(
                offset_url,
                status_code=200,
                json=mock_response_list[1],
                complete_qs=True,
            )
        response = table.all()

    for n, resp in enumerate(response):
        assert dict_equals(resp, mock_records[n])


def test_iterate(table, mock_response_list, mock_records):
    with Mocker() as mock:
        mock.get(
            table.table_url,
            status_code=200,
            json=mock_response_list[0],
            complete_qs=True,
        )
        for n, resp in enumerate(mock_response_list, 1):
            offset = resp.get("offset", None)
            if not offset:
                continue
            params = {"offset": offset}
            offset_url = Request("get", table.table_url, params=params).prepare().url
            mock.get(
                offset_url,
                status_code=200,
                json=mock_response_list[1],
                complete_qs=True,
            )

        pages = []
        for page in table.iterate():
            pages.append(page)

    for n, response in enumerate(mock_response_list):
        assert seq_equals(pages[n], response["records"])


def test_create(table, mock_response_single):
    with Mocker() as mock:
        post_data = mock_response_single["fields"]
        mock.post(
            table.table_url,
            status_code=201,
            json=mock_response_single,
            additional_matcher=match_request_data(post_data),
        )
        resp = table.create(post_data)
    assert dict_equals(resp, mock_response_single)


def test_batch_create(table, mock_records):
    with Mocker() as mock:
        for chunk in _chunk(mock_records, 10):
            mock.post(
                table.table_url,
                status_code=201,
                json={"records": chunk},
            )
        records = [i["fields"] for i in mock_records]
        resp = table.batch_create(records)
    assert seq_equals(resp, mock_records)


@pytest.mark.parametrize("replace,http_method", [(False, "PATCH"), (True, "PUT")])
def test_update(table, mock_response_single, replace, http_method):
    id_ = mock_response_single["id"]
    post_data = mock_response_single["fields"]
    with Mocker() as mock:
        mock.register_uri(
            http_method,
            urljoin(table.table_url, id_),
            status_code=201,
            json=mock_response_single,
            additional_matcher=match_request_data(post_data),
        )
        resp = table.update(id_, post_data, replace=replace)
    assert dict_equals(resp, mock_response_single)


@pytest.mark.parametrize("replace,http_method", [(False, "PATCH"), (True, "PUT")])
def test_batch_update(table, mock_response_batch, replace, http_method):
    records = [
        {"id": x["id"], "fields": x["fields"]} for x in mock_response_batch["records"]
    ]
    with Mocker() as mock:
        for chunk in _chunk(mock_response_batch["records"], 10):
            mock.register_uri(
                http_method,
                table.table_url,
                status_code=201,
                json={"records": chunk},
            )
        resp = table.batch_update(records, replace=replace)

    assert resp == mock_response_batch["records"]


@pytest.mark.parametrize("replace,http_method", [(False, "PATCH"), (True, "PUT")])
def test_batch_upsert(table, mock_response_batch, replace, http_method):
    records = [
        {"id": x["id"], "fields": x["fields"]} for x in mock_response_batch["records"]
    ]
    fields = ["Name"]
    with Mocker() as mock:
        for chunk in _chunk(mock_response_batch["records"], 10):
            mock.register_uri(
                http_method,
                table.table_url,
                status_code=201,
                json={"records": chunk},
            )
        resp = table.batch_upsert(records, key_fields=fields, replace=replace)

    assert resp == mock_response_batch["records"]


def test_batch_upsert__missing_field(table, requests_mock):
    """
    Test that batch_upsert raises an exception if a record in the input
    is missing one of the key_fields, since this will create an error
    on the API.
    """
    with pytest.raises(ValueError):
        table.batch_upsert([{"fields": {"Name": "Alice"}}], key_fields=["Email"])


def test_delete(table, mock_response_single):
    id_ = mock_response_single["id"]
    expected = {"delete": True, "id": id_}
    with Mocker() as mock:
        mock.delete(urljoin(table.table_url, id_), status_code=201, json=expected)
        resp = table.delete(id_)
    assert resp == expected


def test_batch_delete(table, mock_records):
    ids = [i["id"] for i in mock_records]
    with Mocker() as mock:
        for chunk in _chunk(ids, 10):
            json_response = {"records": [{"delete": True, "id": id_} for id_ in chunk]}
            url_match = (
                Request("get", table.table_url, params={"records[]": chunk})
                .prepare()
                .url
            )
            mock.delete(
                url_match,
                status_code=201,
                json=json_response,
            )

        resp = table.batch_delete(ids)
    expected = [{"delete": True, "id": i} for i in ids]
    assert resp == expected


# Helpers


def _chunk(iterable, chunk_size):
    for i in range(0, len(iterable), chunk_size):
        yield iterable[i : i + chunk_size]


def match_request_data(post_data):
    """Custom Matches, check that provided Request data is correct"""

    def _match_request_data(request):
        request_data_fields = request.json()["fields"]
        return dict_equals(request_data_fields, post_data)

    return _match_request_data


def dict_equals(d1, d2):
    return sorted(d1.items()) == sorted(d2.items())


def seq_equals(s1, s2):
    return all(dict_equals(s1, s2) for s1, s2 in zip(s1, s2))
