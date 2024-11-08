from datetime import datetime, timezone
from unittest import mock

import pytest
from requests import Request
from requests_mock import Mocker

from pyairtable import Api, Base, Table
from pyairtable.formulas import AND, EQ, Field
from pyairtable.models.schema import TableSchema
from pyairtable.testing import fake_attachment, fake_id, fake_record
from pyairtable.utils import chunked

NOW = datetime.now(timezone.utc).isoformat()


@pytest.fixture()
def table_schema(sample_json, api, base) -> TableSchema:
    return TableSchema.model_validate(sample_json("TableSchema"))


@pytest.fixture
def mock_schema(table, requests_mock, sample_json):
    table_schema = sample_json("TableSchema")
    table_schema["id"] = table.name = fake_id("tbl")
    return requests_mock.get(
        table.base.urls.tables + "?include=visibleFieldIds",
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
    assert (
        table.urls.records == f"https://api.airtable.com/v0/{base.id}/{table_schema.id}"
    )
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
    assert repr(table) == "<Table base='appLkNDICXNqxSDhG' name='Table Name'>"


def test_schema(base, requests_mock, sample_json):
    """
    Test that we can load schema from API.
    """
    table = base.table("Apartments")
    m = requests_mock.get(base.urls.tables, json=sample_json("BaseSchema"))
    assert isinstance(schema := table.schema(), TableSchema)
    assert m.call_count == 1
    assert schema.id == "tbltp8DGLhqbUmjK1"


def test_id(base, requests_mock, sample_json):
    """
    Test that we load schema from API if we need the ID and don't have it,
    but if we get a name that *looks* like an ID, we trust it.
    """
    m = requests_mock.get(base.urls.tables, json=sample_json("BaseSchema"))

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
    assert table.urls.records == f"https://api.airtable.com/v0/{table_url_suffix}"


def test_chunk(table: Table):
    chunks = [chunk for chunk in chunked([0, 0, 1, 1, 2, 2, 3], 2)]
    assert chunks[0] == [0, 0]
    assert chunks[1] == [1, 1]
    assert chunks[2] == [2, 2]
    assert chunks[3] == [3]


def test_api_key(table: Table, mock_response_single):
    def match_auth_header(request):
        expected_auth_header = "Bearer {}".format(table.api.api_key)
        return (
            "Authorization" in request.headers
            and request.headers["Authorization"] == expected_auth_header
        )

    with Mocker() as m:
        m.get(
            table.urls.record("rec"),
            status_code=200,
            json=mock_response_single,
            additional_matcher=match_auth_header,
        )

        table.get("rec")


def test_get(table: Table, mock_response_single):
    _id = mock_response_single["id"]
    with Mocker() as mock:
        mock.get(table.urls.record(_id), status_code=200, json=mock_response_single)
        resp = table.get(_id)
    assert dict_equals(resp, mock_response_single)


def test_first(table: Table, mock_response_single):
    mock_response = {"records": [mock_response_single]}
    with Mocker() as mock:
        url = Request("get", table.urls.records, params={"maxRecords": 1}).prepare().url
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
        url = table.urls.records_post
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
        url = Request("get", table.urls.records, params={"maxRecords": 1}).prepare().url
        mock.get(
            url,
            status_code=200,
            json=mock_response,
        )
        rv = table.first()
        assert rv is None


def test_all(table, requests_mock, mock_response_list, mock_records):
    requests_mock.get(
        table.urls.records,
        status_code=200,
        json=mock_response_list[0],
        complete_qs=True,
    )
    for n, resp in enumerate(mock_response_list, 1):
        offset = resp.get("offset", None)
        if not offset:
            continue
        requests_mock.get(
            table.urls.records.add_qs(offset=offset),
            status_code=200,
            json=mock_response_list[1],
            complete_qs=True,
        )

    response = table.all()

    for n, resp in enumerate(response):
        assert dict_equals(resp, mock_records[n])


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"view": "Grid view"}, {"view": ["Grid view"]}),
        ({"page_size": 10}, {"pageSize": ["10"]}),
        ({"max_records": 10}, {"maxRecords": ["10"]}),
        ({"fields": ["Name", "Email"]}, {"fields[]": ["Name", "Email"]}),
        ({"formula": "{Status}='Active'"}, {"filterByFormula": ["{Status}='Active'"]}),
        ({"cell_format": "json"}, {"cellFormat": ["json"]}),
        ({"user_locale": "en_US"}, {"userLocale": ["en_US"]}),
        ({"time_zone": "America/New_York"}, {"timeZone": ["America/New_York"]}),
        ({"use_field_ids": True}, {"returnFieldsByFieldId": ["1"]}),
        (
            {"sort": ["Name", "-Email"]},
            {
                "sort[0][direction]": ["asc"],
                "sort[0][field]": ["Name"],
                "sort[1][direction]": ["desc"],
                "sort[1][field]": ["Email"],
            },
        ),
    ],
)
def test_all__params(table, requests_mock, kwargs, expected):
    """
    Test that parameters to all() get translated to query string correctly.
    """
    m = requests_mock.get(table.urls.records, status_code=200, json={"records": []})
    table.all(**kwargs)
    assert m.last_request.qs == expected


def test_iterate(table: Table, mock_response_list, mock_records):
    with Mocker() as mock:
        mock.get(
            table.urls.records,
            status_code=200,
            json=mock_response_list[0],
            complete_qs=True,
        )
        for n, resp in enumerate(mock_response_list, 1):
            offset = resp.get("offset", None)
            if not offset:
                continue
            params = {"offset": offset}
            offset_url = Request("get", table.urls.records, params=params).prepare().url
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


def test_iterate__formula_conversion(table):
    """
    Test that .iterate() will convert a Formula to a str.
    """
    with mock.patch("pyairtable.Api.iterate_requests") as m:
        table.all(formula=AND(EQ(Field("Name"), "Alice")))

    m.assert_called_once_with(
        method="get",
        url=table.urls.records,
        fallback=mock.ANY,
        options={
            "formula": "AND({Name}='Alice')",
        },
    )


def test_create(table: Table, mock_response_single):
    with Mocker() as mock:
        post_data = mock_response_single["fields"]
        mock.post(
            table.urls.records,
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
                table.urls.records,
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
            table.urls.record(id_),
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
            table.urls.records,
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
            table.urls.records,
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
        mock.delete(table.urls.record(id_), status_code=201, json=expected)
        resp = table.delete(id_)
    assert resp == expected


@pytest.mark.parametrize("container", [list, tuple, iter])
def test_batch_delete(table: Table, container, mock_records):
    ids = [i["id"] for i in mock_records]
    with Mocker() as mock:
        for chunk in _chunk(ids, 10):
            json_response = {"records": [{"deleted": True, "id": id_} for id_ in chunk]}
            url_match = (
                Request("get", table.urls.records, params={"records[]": chunk})
                .prepare()
                .url
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
        table.urls.fields,
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


fake_upsert = {"updatedRecords": [], "createdRecords": [], "records": []}


def test_use_field_ids__get_record(table, monkeypatch, requests_mock):
    """
    Test that setting api.use_field_ids=True will change the default behavior
    (but not the explicit behavior) of Table.get()
    """
    record = fake_record()
    url = table.urls.record(record_id := record["id"])
    m = requests_mock.register_uri("GET", url, json=record)

    # by default, we don't pass the param at all
    table.get(record_id)
    assert m.called
    assert "returnFieldsByFieldId" not in m.last_request.qs

    # if use_field_ids=True, we should pass the param...
    monkeypatch.setattr(table.api, "use_field_ids", True)
    m.reset()
    table.get(record_id)
    assert m.called
    assert m.last_request.qs["returnFieldsByFieldId"] == ["1"]

    # ...but we can override it
    m.reset()
    table.get(record_id, use_field_ids=False)
    assert m.called
    assert m.last_request.qs["returnFieldsByFieldId"] == ["0"]


@pytest.mark.parametrize("method_name", ("all", "first"))
def test_use_field_ids__get_records(table, monkeypatch, requests_mock, method_name):
    """
    Test that setting api.use_field_ids=True will change the default behavior
    (but not the explicit behavior) of Table.all() and Table.first()
    """
    m = requests_mock.register_uri("GET", table.urls.records, json={"records": []})

    # by default, we don't pass the param at all
    method = getattr(table, method_name)
    method()
    assert m.called
    assert "returnFieldsByFieldId" not in m.last_request.qs

    # if use_field_ids=True, we should pass the param...
    monkeypatch.setattr(table.api, "use_field_ids", True)
    m.reset()
    method()
    assert m.called
    assert m.last_request.qs["returnFieldsByFieldId"] == ["1"]

    # ...but we can override it
    m.reset()
    method(use_field_ids=False)
    assert m.called
    assert m.last_request.qs["returnFieldsByFieldId"] == ["0"]


@pytest.mark.parametrize(
    "method_name,method_args,http_method,suffix,response",
    [
        ("create", ({"fields": {}}), "POST", "", fake_record()),
        ("update", ("rec123", {}), "PATCH", "rec123", fake_record()),
        ("batch_create", ([fake_record()],), "POST", "", {"records": []}),
        ("batch_update", ([fake_record()],), "PATCH", "", {"records": []}),
        ("batch_upsert", ([fake_record()], ["Key"]), "PATCH", "", fake_upsert),
    ],
)
def test_use_field_ids__post(
    table,
    monkeypatch,
    requests_mock,
    method_name,
    method_args,
    http_method,
    suffix,
    response,
):
    """
    Test that setting api.use_field_ids=True will change the default behavior
    (but not the explicit behavior) of the create/update API methods on Table.
    """
    url = table.urls.records / suffix
    print(f"{url=}")
    m = requests_mock.register_uri(http_method, url.rstrip("/"), json=response)

    # by default, the param is False
    method = getattr(table, method_name)
    method(*method_args)
    assert m.call_count == 1
    assert m.last_request.json()["returnFieldsByFieldId"] is False

    # if use_field_ids=True, we should pass the param...
    monkeypatch.setattr(table.api, "use_field_ids", True)
    m.reset()
    method(*method_args)
    assert m.call_count == 1
    assert m.last_request.json()["returnFieldsByFieldId"] is True

    # ...but we can override it
    m.reset()
    method(*method_args, use_field_ids=False)
    assert m.call_count == 1
    assert m.last_request.json()["returnFieldsByFieldId"] is False


RECORD_ID = fake_id()
FIELD_ID = fake_id("fld")


@pytest.fixture
def mock_upload_attachment(requests_mock, table):
    return requests_mock.post(
        f"https://content.airtable.com/v0/{table.base.id}/{RECORD_ID}/{FIELD_ID}/uploadAttachment",
        status_code=200,
        json={
            "id": RECORD_ID,
            "createdTime": NOW,
            "fields": {FIELD_ID: [fake_attachment()]},
        },
    )


@pytest.mark.parametrize("content", [b"Hello, World!", "Hello, World!"])
def test_upload_attachment(mock_upload_attachment, table, content):
    """
    Test that we can upload an attachment to a record.
    """
    table.upload_attachment(RECORD_ID, FIELD_ID, "sample.txt", content)
    assert mock_upload_attachment.last_request.json() == {
        "contentType": "text/plain",
        "file": "SGVsbG8sIFdvcmxkIQ==\n",  # base64 encoded "Hello, World!"
        "filename": "sample.txt",
    }


def test_upload_attachment__no_content_type(mock_upload_attachment, table, tmp_path):
    """
    Test that we can upload an attachment to a record.
    """
    tmp_file = tmp_path / "sample_no_extension"
    tmp_file.write_bytes(b"Hello, World!")

    with pytest.warns(Warning, match="Could not guess content-type"):
        table.upload_attachment(RECORD_ID, FIELD_ID, tmp_file)

    assert mock_upload_attachment.last_request.json() == {
        "contentType": "application/octet-stream",
        "file": "SGVsbG8sIFdvcmxkIQ==\n",  # base64 encoded "Hello, World!"
        "filename": "sample_no_extension",
    }


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
