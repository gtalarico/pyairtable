from posixpath import join as urljoin

import pytest
from requests import Request
from requests_mock import Mocker

from pyairtable import Api, Base, Table
from pyairtable.models.schema import TableSchema
from pyairtable.testing import fake_id, fake_record
from pyairtable.utils import chunked


@pytest.fixture()
def table_schema(sample_json) -> TableSchema:
    return TableSchema.parse_obj(sample_json("TableSchema"))


@pytest.fixture
def mock_schema(table, requests_mock, sample_json):
    table_schema = sample_json("TableSchema")
    table_schema["id"] = table.name = fake_id("tbl")
    return requests_mock.get(
        table.base.meta_url("tables") + "?include=visibleFieldIds",
        json={"tables": [table_schema]},
    )


def test_constructor(base: Base):
    """
    Test the constructor.
    """
    table = Table(None, base, "table_name")
    assert table.api == base.api
    assert table.base == base
    assert table.name == "table_name"


def test_constructor_with_schema(base: Base, table_schema: TableSchema):
    table = Table(None, base, table_schema)
    assert table.api == base.api
    assert table.base == base
    assert table.name == table_schema.name
    assert table.url == f"https://api.airtable.com/v0/{base.id}/{table_schema.id}"
    assert (
        repr(table)
        == f"<Table base='{base.id}' id='{table_schema.id}' name='{table_schema.name}'>"
    )


def test_deprecated_constructor(api: Api, base: Base):
    """
    Test that "legacy" constructor (passing strings instead of instances)
    will throw deprecation warning, but it _will_ work.
    """
    with pytest.warns(DeprecationWarning):
        table = Table(api.api_key, base.id, "table_name", timeout=(1, 99))

    assert table.api.api_key == api.api_key
    assert table.api.timeout == (1, 99)
    assert table.base.id == base.id
    assert table.name == "table_name"


def test_invalid_constructor(api, base):
    """
    Test that we get a TypeError if passing invalid args to Table.
    """
    for args in [
        [api, "base_id", "table_name"],
        ["api_key", base, "table_name"],
        [api, base, "table_name"],
        [None, base, -1],
    ]:
        kwargs = args.pop() if isinstance(args[-1], dict) else {}
        with pytest.raises(TypeError):
            print(args, kwargs)
            Table(*args, **kwargs)


def test_repr(table: Table):
    assert repr(table) == "<Table base='appJMY16gZDQrMWpA' name='Table Name'>"


def test_schema(base, requests_mock, sample_json):
    """
    Test that we can load schema from API.
    """
    table = base.table("Apartments")
    m = requests_mock.get(base.meta_url("tables"), json=sample_json("BaseSchema"))
    assert isinstance(schema := table.schema(), TableSchema)
    assert m.call_count == 1
    assert schema.id == "tbltp8DGLhqbUmjK1"


def test_id(base, requests_mock, sample_json):
    """
    Test that we load schema from API if we need the ID and don't have it,
    but if we get a name that *looks* like an ID, we trust it.
    """
    m = requests_mock.get(base.meta_url("tables"), json=sample_json("BaseSchema"))

    table = base.table("tbltp8DGLhqbUmjK1")
    assert table.id == "tbltp8DGLhqbUmjK1"
    assert m.call_count == 0

    table = base.table("Apartments")
    assert table.id == "tbltp8DGLhqbUmjK1"
    assert m.call_count == 1


@pytest.mark.parametrize(
    "base_id,table_name,table_url_suffix",
    [
        ("abc", "My Table", "abc/My%20Table"),
        ("abc", "SomeTable", "abc/SomeTable"),
        ("abc", "Table-fake", "abc/Table-fake"),
    ],
)
def test_url(api: Api, base_id, table_name, table_url_suffix):
    table = api.table(base_id, table_name)
    assert table.url == f"https://api.airtable.com/v0/{table_url_suffix}"


def test_chunk(table: Table):
    chunks = [chunk for chunk in chunked([0, 0, 1, 1, 2, 2, 3], 2)]
    assert chunks[0] == [0, 0]
    assert chunks[1] == [1, 1]
    assert chunks[2] == [2, 2]
    assert chunks[3] == [3]


def test_record_url(table: Table):
    rv = table.record_url("xxx")
    assert rv == urljoin(table.url, "xxx")


def test_api_key(table: Table, mock_response_single):
    def match_auth_header(request):
        expected_auth_header = "Bearer {}".format(table.api.api_key)
        return (
            "Authorization" in request.headers
            and request.headers["Authorization"] == expected_auth_header
        )

    with Mocker() as m:
        m.get(
            table.record_url("rec"),
            status_code=200,
            json=mock_response_single,
            additional_matcher=match_auth_header,
        )

        table.get("rec")


def test_get(table: Table, mock_response_single):
    _id = mock_response_single["id"]
    with Mocker() as mock:
        mock.get(table.record_url(_id), status_code=200, json=mock_response_single)
        resp = table.get(_id)
    assert dict_equals(resp, mock_response_single)


def test_first(table: Table, mock_response_single):
    mock_response = {"records": [mock_response_single]}
    with Mocker() as mock:
        url = Request("get", table.url, params={"maxRecords": 1}).prepare().url
        mock.get(
            url,
            status_code=200,
            json=mock_response,
        )
        rv = table.first()
        assert rv
    assert rv["id"] == mock_response_single["id"]


def test_first_via_post(table: Table, mock_response_single):
    mock_response = {"records": [mock_response_single]}
    with Mocker() as mock:
        url = table.url + "/listRecords"
        formula = f"RECORD_ID() != '{'x' * 17000}'"
        mock_endpoint = mock.post(url, status_code=200, json=mock_response)
        rv = table.first(formula=formula)

    assert mock_endpoint.last_request.json() == {
        "filterByFormula": formula,
        "maxRecords": 1,
        "pageSize": 1,
    }
    assert rv == mock_response_single


def test_first_none(table: Table, mock_response_single):
    mock_response = {"records": []}
    with Mocker() as mock:
        url = Request("get", table.url, params={"maxRecords": 1}).prepare().url
        mock.get(
            url,
            status_code=200,
            json=mock_response,
        )
        rv = table.first()
        assert rv is None


def test_all(table: Table, mock_response_list, mock_records):
    with Mocker() as mock:
        mock.get(
            table.url,
            status_code=200,
            json=mock_response_list[0],
            complete_qs=True,
        )
        for n, resp in enumerate(mock_response_list, 1):
            offset = resp.get("offset", None)
            if not offset:
                continue
            offset_url = table.url + "?offset={}".format(offset)
            mock.get(
                offset_url,
                status_code=200,
                json=mock_response_list[1],
                complete_qs=True,
            )
        response = table.all()

    for n, resp in enumerate(response):
        assert dict_equals(resp, mock_records[n])


def test_iterate(table: Table, mock_response_list, mock_records):
    with Mocker() as mock:
        mock.get(
            table.url,
            status_code=200,
            json=mock_response_list[0],
            complete_qs=True,
        )
        for n, resp in enumerate(mock_response_list, 1):
            offset = resp.get("offset", None)
            if not offset:
                continue
            params = {"offset": offset}
            offset_url = Request("get", table.url, params=params).prepare().url
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


def test_create(table: Table, mock_response_single):
    with Mocker() as mock:
        post_data = mock_response_single["fields"]
        mock.post(
            table.url,
            status_code=201,
            json=mock_response_single,
            additional_matcher=match_request_data(post_data),
        )
        resp = table.create(post_data)
    assert dict_equals(resp, mock_response_single)


@pytest.mark.parametrize("container", [list, tuple, iter])
def test_batch_create(table: Table, container, mock_records):
    with Mocker() as mock:
        for chunk in _chunk(mock_records, 10):
            mock.post(
                table.url,
                status_code=201,
                json={"records": chunk},
            )
        records = [i["fields"] for i in mock_records]
        resp = table.batch_create(container(records))
    assert seq_equals(resp, mock_records)


@pytest.mark.parametrize("replace,http_method", [(False, "PATCH"), (True, "PUT")])
def test_update(table: Table, mock_response_single, replace, http_method):
    id_ = mock_response_single["id"]
    post_data = mock_response_single["fields"]
    with Mocker() as mock:
        mock.register_uri(
            http_method,
            urljoin(table.url, id_),
            status_code=201,
            json=mock_response_single,
            additional_matcher=match_request_data(post_data),
        )
        resp = table.update(id_, post_data, replace=replace)
    assert dict_equals(resp, mock_response_single)


@pytest.mark.parametrize("container", [list, tuple, iter])
@pytest.mark.parametrize("replace,http_method", [(False, "PATCH"), (True, "PUT")])
def test_batch_update(table: Table, container, replace, http_method):
    records = [fake_record(fieldvalue=index) for index in range(50)]
    with Mocker() as mock:
        mock.register_uri(
            http_method,
            table.url,
            response_list=[
                {"json": {"records": chunk}} for chunk in table.api.chunked(records)
            ],
        )
        resp = table.batch_update(container(records), replace=replace)

    assert resp == records


@pytest.mark.parametrize("container", [list, tuple, iter])
@pytest.mark.parametrize("replace,http_method", [(False, "PATCH"), (True, "PUT")])
def test_batch_upsert(table: Table, container, replace, http_method, monkeypatch):
    field_name = "Name"
    exists1 = fake_record({field_name: "Exists 1"})
    exists2 = fake_record({field_name: "Exists 2"})
    created = fake_record({field_name: "Does not exist"})
    payload = [
        {"id": exists1["id"], "fields": {field_name: "Exists 1"}},
        {"fields": {field_name: "Exists 2"}},
        {"fields": {field_name: "Does not exist"}},
    ]
    responses = [
        {"createdRecords": [], "updatedRecords": [exists1["id"]], "records": [exists1]},
        {"createdRecords": [], "updatedRecords": [exists2["id"]], "records": [exists2]},
        {"createdRecords": [created["id"]], "updatedRecords": [], "records": [created]},
    ]
    with Mocker() as mock:
        mock.register_uri(
            http_method,
            table.url,
            response_list=[{"json": response} for response in responses],
        )
        monkeypatch.setattr(table.api, "MAX_RECORDS_PER_REQUEST", 1)
        resp = table.batch_upsert(
            container(payload), key_fields=[field_name], replace=replace
        )

    assert resp == {
        "createdRecords": [created["id"]],
        "updatedRecords": [exists1["id"], exists2["id"]],
        "records": [exists1, exists2, created],
    }


def test_batch_upsert__missing_field(table: Table, requests_mock):
    """
    Test that batch_upsert raises an exception if a record in the input
    is missing one of the key_fields, since this will create an error
    on the API.
    """
    with pytest.raises(ValueError):
        table.batch_upsert([{"fields": {"Name": "Alice"}}], key_fields=["Email"])


def test_delete(table: Table, mock_response_single):
    id_ = mock_response_single["id"]
    expected = {"deleted": True, "id": id_}
    with Mocker() as mock:
        mock.delete(urljoin(table.url, id_), status_code=201, json=expected)
        resp = table.delete(id_)
    assert resp == expected


@pytest.mark.parametrize("container", [list, tuple, iter])
def test_batch_delete(table: Table, container, mock_records):
    ids = [i["id"] for i in mock_records]
    with Mocker() as mock:
        for chunk in _chunk(ids, 10):
            json_response = {"records": [{"deleted": True, "id": id_} for id_ in chunk]}
            url_match = (
                Request("get", table.url, params={"records[]": chunk}).prepare().url
            )
            mock.delete(
                url_match,
                status_code=201,
                json=json_response,
            )

        resp = table.batch_delete(container(ids))
    expected = [{"deleted": True, "id": i} for i in ids]
    assert resp == expected


def test_create_field(table, mock_schema, requests_mock, sample_json):
    """
    Tests the API for creating a field (but without actually performing the operation).
    """
    mock_create = requests_mock.post(
        table.meta_url("fields"),
        json=sample_json("field_schema/SingleSelectFieldSchema"),
    )

    # Ensure we have pre-loaded our schema
    table.schema()
    assert mock_schema.call_count == 1

    # Create the field
    choices = ["Todo", "In progress", "Done"]
    fld = table.create_field(
        "Status",
        "singleSelect",
        description="field description",
        options={"choices": choices},
    )
    assert mock_create.call_count == 1
    assert mock_create.request_history[-1].json() == {
        "name": "Status",
        "type": "singleSelect",
        "description": "field description",
        "options": {"choices": choices},
    }

    # Test the result we got back
    assert fld.id == "fldqCjrs1UhXgHUIc"
    assert fld.name == "Status"
    assert {c.name for c in fld.options.choices} == set(choices)

    # Test that we constructed the URL correctly
    assert fld._url.endswith(f"/{table.base.id}/tables/{table.name}/fields/{fld.id}")

    # Test that the schema has been updated without a second API call
    assert table._schema.field(fld.id).name == "Status"
    assert mock_schema.call_count == 1


def test_delete_view(table, mock_schema, requests_mock):
    view = table.schema().view("Grid view")
    m = requests_mock.delete(view._url)
    view.delete()
    assert m.call_count == 1


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
