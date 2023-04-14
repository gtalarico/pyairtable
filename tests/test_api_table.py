import pytest
from posixpath import join as urljoin
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
    assert table.table_url == "{0}/{1}".format(table.API_URL, table_url_suffix)


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


def test_update(table, mock_response_single):
    id_ = mock_response_single["id"]
    post_data = mock_response_single["fields"]
    with Mocker() as mock:
        mock.patch(
            urljoin(table.table_url, id_),
            status_code=201,
            json=mock_response_single,
            additional_matcher=match_request_data(post_data),
        )
        resp = table.update(id_, post_data)
    assert dict_equals(resp, mock_response_single)


def test_batch_update(table, mock_response_batch):
    records = [
        {"id": x["id"], "fields": x["fields"]} for x in mock_response_batch["records"]
    ]
    with Mocker() as mock:
        for chunk in _chunk(mock_response_batch["records"], 10):
            mock.patch(
                table.table_url,
                status_code=201,
                json={"records": chunk},
            )
        #
        resp = table.batch_update(records)
    assert resp == mock_response_batch["records"]


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

def test_comment_mentioned(mock_comment_single):
    _usr_mentioned = list(mock_comment_single["mentioned"])[0]
    assert _usr_mentioned in mock_comment_single['text']

def test_comment_update(table, mock_comment_update, mock_response_single):
    comment_id_ = mock_comment_update["id"]
    record_id_ = mock_response_single["id"]
    text = mock_comment_update['text']

    expected = {"author":{"email":"foo@bar.com","id":"usrL2PNC5o3H4lBEi","name":"Foo Bar"},"createdTime":"2021-03-01T09:00:00.000Z","id": comment_id_,"lastUpdatedTime":"2021-04-01T09:00:00.000Z","text":"Update, world!"}
    with Mocker() as mock:
        mock.patch(urljoin(table.table_url, record_id_, 'comments', comment_id_), status_code=200, json=expected)
        resp = table.update_comment(record_id_, comment_id_, text)
    assert resp == expected

def test_comment_delete(table, mock_comment_update, mock_response_single):
    comment_id_ = mock_comment_update["id"]
    record_id_ = mock_response_single["id"]
    expected = {"delete": True, "id": comment_id_}

    with Mocker() as mock:
        mock.delete(urljoin(table.table_url, record_id_, 'comments', comment_id_), status_code=200, json=expected)
        resp = table.delete_comment(record_id_, comment_id_)
    assert resp == expected

def test_comment_create(table, mock_comment_single, mock_response_single):
    record_id_ = mock_response_single["id"]
    text = mock_comment_single['text']
    expected = mock_comment_single

    with Mocker() as mock:
        mock.post(urljoin(table.table_url, record_id_, 'comments'), status_code=200, json=expected)
        resp = table.create_comment(record_id_, text)
    assert resp == expected

def test_comment_list(table, mock_comments, mock_response_single):
    record_id_ = mock_response_single["id"]
    expected = {"comments":mock_comments}
    with Mocker() as mock:
        mock.get(urljoin(table.table_url, record_id_, 'comments'), status_code=200, json=expected)
        resp = table.get_comments(record_id_)
    assert resp == expected['comments']

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
