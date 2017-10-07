from airtable import Airtable
import pytest
from six.moves.urllib import parse


@pytest.fixture
def db_key():
    return 'app0011kkk01'


@pytest.fixture
def table_names():
    return {'Test table 1': 'Test%20table%201',
            'Test/Table 2': 'Test%2FTable%202',
            'Another (test) table': 'Another%20%28test%29%20table',
            'A & test & table': 'A%20%26%20test%20%26%20table',
            'percentage % table': 'percentage%20%25%20table'
            }


@pytest.fixture
def baseurl(db_key):
    url = parse.urljoin('https://api.airtable.com/v0/', db_key + '/')
    return url


def _make_url(url, table_escaped):
    # return parse.urljoin(str(url + '/'), table_escaped)
    return parse.urljoin(url, table_escaped)


def test_url_escape(db_key, table_names, baseurl, monkeypatch):
    def rettrue(*args):
        return True
    monkeypatch.setattr(Airtable, 'validate_session', rettrue)
    print('baseurl: {}'.format(baseurl))
    for name, escaped in table_names.items():
        tmp_at = Airtable(base_key=db_key, table_name=name, api_key='key1234')
        assert str(tmp_at.url_table) == _make_url(baseurl, escaped)
