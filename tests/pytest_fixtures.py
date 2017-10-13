import os
import pytest
from requests_mock import Mocker
from posixpath import join as urljoin
from six.moves.urllib.parse import urlencode, quote

from airtable import Airtable


def build_url(base_key, table_name, params=None):
    """ Builds Airtable Api Url Manually for mock testing """
    table_name = quote(table_name)
    url = urljoin(Airtable.API_URL, base_key, table_name)
    if params:
        url += '?' + urlencode(params)
    return url

fake_api_key = 'FakeApiKey'
real_api_key = os.environ['AIRTABLE_API_KEY']
base_key = 'appJMY16gZDQrMWpA'
table_name = 'TABLE READ'
table_url = build_url(base_key,table_name)

@pytest.fixture(scope='session')
def mock_airtable():
    """ Creates a Mock Airtable Base  """
    with Mocker() as m:
        mock_url = build_url(base_key, table_name, params={'maxRecords': 1})
        m.get(mock_url, status_code=200)
        airtable = Airtable(base_key, table_name)
    return airtable

@pytest.fixture(scope='session')
def airtable():
    """ Creates a Mock Airtable Base  """
    airtable = Airtable(base_key, table_name)
    clear_table(airtable)
    populate_table(airtable)
    return airtable

def clear_table(airtable):
    records = airtable.get_all()
    if records:
        print('Clearing table...')
        airtable.mirror([])
        print('Table cleared')

def populate_table(airtable):
    for i in range(1, 150):
        row = {'COLUMN_INT': str(i), 'COLUMN_STR': i}
        resp = airtable_write.insert(row)
        assert resp.ok

