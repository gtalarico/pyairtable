import pytest

from airtable import Airtable
from .pytest_fixtures import mock_airtable


@pytest.fixture
def table_names():
    """Dict of some test table names with characters that are not url safe with
    url-escaped versions.
    """
    return {'Test table 1': 'Test%20table%201',
            'Test/Table 2': 'Test%2FTable%202',
            'Another (test) table': 'Another%20%28test%29%20table',
            'A & test & table': 'A%20%26%20test%20%26%20table',
            'percentage % table': 'percentage%20%25%20table'
            }

def test_url_escape(base_key, table_names, api_key):
    """Test for proper escaping of urls including unsafe characters in table
    names (which airtable allows).
    """
    for table_name, escaped in table_names.items():
        with Mocker() as m:
            url = build_url_manual(base_key, table_name,
                                   params={'maxRecords': 1})
            m.get(url, status_code=200)
            airtable = Airtable(base_key, table_name, api_key=api_key)

        assert str(tmp_at.url_table) == _make_url(baseurl, escaped),\
            "Class-generated url should be properly escaped."
