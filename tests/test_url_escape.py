import pytest


@pytest.mark.parametrize(
    "table_name,escaped",
    [
        ("Test table 1", "Test%20table%201"),
        ("Test/Table 2", "Test%2FTable%202"),
        ("Another (test) table", "Another%20%28test%29%20table"),
        ("A & test & table", "A%20%26%20test%20%26%20table"),
        ("percentage % table", "percentage%20%25%20table"),
    ],
)
def test_url_escape(base, table_name, escaped):
    """
    Test for proper escaping of urls including unsafe characters in
    table names (which Airtable *will* allow).
    """
    table = base.table(table_name)
    assert table.url.endswith(escaped)
