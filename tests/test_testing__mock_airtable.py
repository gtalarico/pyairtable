from unittest.mock import ANY

import pytest

from pyairtable import testing as T


@pytest.fixture
def mock_airtable(requests_mock):
    with T.MockAirtable() as m:
        yield m


def test_not_reentrant():
    """
    Test that nested MockAirtable contexts raise an error.
    """
    mocked = T.MockAirtable()
    with mocked:
        with pytest.raises(RuntimeError):
            with mocked:
                pass


def test_multiple_nested_contexts():
    """
    Test that nested MockAirtable contexts raise an error.
    """
    with T.MockAirtable():
        with pytest.raises(RuntimeError):
            with T.MockAirtable():
                pass


def test_add_records__ids(mock_airtable, table):
    fake_records = [T.fake_record() for _ in range(3)]
    mock_airtable.add_records(table.base.id, table.name, fake_records)
    assert table.all() == fake_records


def test_add_records__ids_kwarg(mock_airtable, table):
    fake_records = [T.fake_record() for _ in range(3)]
    mock_airtable.add_records(table.base.id, table.name, records=fake_records)
    assert table.all() == fake_records


def test_add_records__kwarg(mock_airtable, table):
    fake_records = [T.fake_record() for _ in range(3)]
    mock_airtable.add_records(table, records=fake_records)
    assert table.all() == fake_records


def test_add_records__missing_kwarg(mock_airtable, table):
    with pytest.raises(TypeError, match="add_records missing keyword"):
        mock_airtable.add_records(table)
    with pytest.raises(TypeError, match="add_records missing keyword"):
        mock_airtable.add_records("base", "table")


def test_add_records__invalid_types(mock_airtable):
    with pytest.raises(
        TypeError,
        match=r"add_records expected \(str, str, \.\.\.\), got \(int, float\)",
    ):
        mock_airtable.add_records(1, 2.0, records=[])


def test_add_records__invalid_kwarg(mock_airtable, table):
    with pytest.raises(
        TypeError,
        match="add_records got unexpected keyword arguments: asdf",
    ):
        mock_airtable.add_records(table, records=[], asdf=1)


@pytest.fixture
def mock_records(mock_airtable, table):
    mock_records = [T.fake_record() for _ in range(5)]
    mock_airtable.add_records(table, mock_records)
    return mock_records


@pytest.fixture
def mock_record(mock_records):
    return mock_records[0]


def test_set_records(mock_airtable, mock_records, table):
    replace = [T.fake_record()]
    mock_airtable.set_records(table, replace)
    assert table.all() == replace


def test_set_records__ids(mock_airtable, mock_records, table):
    replace = [T.fake_record()]
    mock_airtable.set_records(table.base.id, table.name, replace)
    assert table.all() == replace


def test_set_records__ids_kwarg(mock_airtable, mock_records, table):
    replace = [T.fake_record()]
    mock_airtable.set_records(table.base.id, table.name, records=replace)
    assert table.all() == replace


def test_set_records__kwarg(mock_airtable, mock_records, table):
    replace = [T.fake_record()]
    mock_airtable.set_records(table, records=replace)
    assert table.all() == replace


@pytest.mark.parametrize(
    "funcname,expected",
    [
        ("all", "mock_records"),
        ("iterate", "[mock_records]"),
        ("first", "mock_records[0]"),
    ],
)
def test_table_iterate(mock_records, table, funcname, expected):
    expected = eval(expected, {}, {"mock_records": mock_records})
    assert getattr(table, funcname)() == expected


def test_table_get(mock_record, table):
    assert table.get(mock_record["id"]) == mock_record


def test_table_create(mock_airtable, table):
    record = table.create(T.fake_record()["fields"])
    assert record in table.all()


def test_table_update(mock_record, table):
    table.update(mock_record["id"], {"Name": "Bob"})
    assert table.get(mock_record["id"])["fields"]["Name"] == "Bob"


def test_table_delete(mock_record, table):
    table.delete(mock_record["id"])
    assert mock_record not in table.all()


def test_table_batch_create(mock_airtable, mock_records, table):
    mock_airtable.clear()
    table.batch_create(mock_records)
    assert all(r in table.all() for r in mock_records)


def test_table_batch_update(mock_records, table):
    table.batch_update(
        [{"id": record["id"], "fields": {"Name": "Bob"}} for record in mock_records]
    )
    assert all(r["fields"]["Name"] == "Bob" for r in table.all())


def test_table_batch_delete(mock_records, table):
    table.batch_delete([r["id"] for r in mock_records])
    assert table.all() == []


def test_table_batch_upsert(mock_airtable, table):
    """
    Test that MockAirtable actually performs upsert logic correctly.
    """
    mock_airtable.clear()
    mock_airtable.add_records(
        table,
        [
            {"id": "rec001", "fields": {"Name": "Alice"}},
            {"id": "rec002", "fields": {"Name": "Bob"}},
            {"id": "rec003", "fields": {"Name": "Carol"}},
        ],
    )
    table.batch_upsert(
        records=[
            # matches by Name to rec001
            {"fields": {"Name": "Alice", "Email": "alice@example.com"}},
            # matches by Name to rec002
            {"fields": {"Name": "Bob", "Email": "bob@example.com"}},
            # matches by id to rec003
            {"id": "rec003", "fields": {"Email": "carol@example.com"}},
            # no match; will create the record
            {"fields": {"Name": "Dave", "Email": "dave@example.com"}},
        ],
        key_fields=["Name"],
    )
    assert table.all() == [
        {
            "id": "rec001",
            "createdTime": ANY,
            "fields": {"Name": "Alice", "Email": "alice@example.com"},
        },
        {
            "id": "rec002",
            "createdTime": ANY,
            "fields": {"Name": "Bob", "Email": "bob@example.com"},
        },
        {
            "id": "rec003",
            "createdTime": ANY,
            "fields": {"Name": "Carol", "Email": "carol@example.com"},
        },
        {
            "id": ANY,
            "createdTime": ANY,
            "fields": {"Name": "Dave", "Email": "dave@example.com"},
        },
    ]


def test_table_batch_upsert__invalid_id(mock_airtable, table):
    with pytest.raises(KeyError):
        table.batch_upsert(
            records=[
                # record does not exist
                {"id": "rec999", "fields": {"Name": "Alice"}}
            ],
            key_fields=["Name"],
        )


@pytest.mark.parametrize(
    "expr",
    [
        "base.collaborators()",
        "base.create_table('Name', fields=[])",
        "base.delete()",
        "base.shares()",
        "base.webhooks()",
        "table.add_comment('recordId', 'value')",
        "table.comments('recordId')",
        "table.create_field('name', 'type')",
        "table.schema()",
    ],
)
def test_unhandled_methods(mock_airtable, monkeypatch, expr, api, base, table):
    """
    Test that unhandled methods raise an error.
    """
    with pytest.raises(RuntimeError):
        eval(expr, {}, {"api": api, "base": base, "table": table})


def test_passthrough(mock_airtable, requests_mock, base, monkeypatch):
    """
    Test that we can temporarily pass through unhandled methods to the requests library.
    """
    requests_mock.get(base.urls.tables, json={"tables": []})

    with monkeypatch.context() as mctx:
        mctx.setattr(mock_airtable, "passthrough", True)
        assert base.schema(force=True).tables == []  # no RuntimeError

    with mock_airtable.enable_passthrough():
        assert base.schema(force=True).tables == []  # no RuntimeError
        with mock_airtable.disable_passthrough():
            with pytest.raises(RuntimeError):
                base.schema(force=True)

    with mock_airtable.set_passthrough(True):
        assert base.schema(force=True).tables == []  # no RuntimeError

    with mock_airtable.set_passthrough(False):
        with pytest.raises(RuntimeError):
            base.schema(force=True)
