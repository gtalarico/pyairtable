import os
import json
import pytest
from collections import OrderedDict, defaultdict
from requests_mock import Mocker
from posixpath import join as urljoin
from six.moves.urllib.parse import urlencode, quote

from airtable import Airtable


def build_url(base_key, table_name, params=None):
    """ Builds Airtable Api Url Manually for mock testing """

    # TODO: Build Url Params
    table_name = quote(table_name, safe='')
    url = urljoin(Airtable.API_URL, base_key, table_name)
    if params:
        params = OrderedDict(sorted(params.items()))
        url += '?' + urlencode(params)
    return url

# Constants
fake_api_key = 'FakeApiKey'
api_key = os.environ['AIRTABLE_API_KEY']
base_key = 'appJMY16gZDQrMWpA'
table_name = 'Table Name'
table_url = build_url(base_key, table_name)


@pytest.fixture(scope='class')
def mock_airtable():
    """ Creates a Mock Airtable Base  """
    with Mocker() as m:
        mock_url = build_url(base_key, table_name, params={'maxRecords': 1})
        m.get(mock_url, status_code=200)
        airtable = Airtable(base_key, table_name, api_key=fake_api_key)
    return airtable


@pytest.fixture(scope='class')
def airtable():
    """ Creates a Mock Airtable Base  """
    airtable = Airtable(base_key, table_name, api_key=api_key)
    return airtable


@pytest.fixture(scope='class')
def clean_airtable():
    airtable = Airtable(base_key, table_name, api_key=api_key)
    reset_table(airtable)
    yield
    reset_table(airtable)


@pytest.fixture(scope='class')
def reset_table(airtable):
    print('>>> Resetting Table')
    data = table_data()

    records = airtable.get_all(sort='COLUMN_INT')
    for n, record in enumerate(records, 1):
        try:
            row = data[n]
        except IndexError:
            airtable.delete(record['id'])
            print('>>> Deleting Record: {}'.format(record))

    records = airtable.get_all(sort='COLUMN_INT')
    for n, row in enumerate(data, 0):
        try:
            record = records[n]
        except IndexError:
            print('>>> Creating Record: {}'.format(row))
            airtable.insert(row)
        else:
            if row != record['fields']:
                airtable.replace(record['id'], row)
                print('>>> Updating Record: {}'.format(record))

    print('>>> Test Table Reset Done')


def table_data():
    data = []
    for i in range(1, 105):
        row = {'COLUMN_INT': i, 'COLUMN_STR': str(i)}
        data.append(row)
    data.append(row)  # Create a duplicate at the end for search testing
    return data

"""

Once Reset Actual Test Table should look like the table below.
The data will be populate by the test suite, but the columns must
be configured properly:

 Table Name: 'Table Name'
 _____________________________________
| COLUMN_INT (int) | COLUMN_STR (str) |
 -------------------------------------
|        1.0       |       '1'        |
|        2.0       |       '2'        |
|        3.0       |       '4'        |
|        ...       |       ...        |
|       104.0      |      '104'       |
|       104.0      |      '104'       |
 -------------------------------------

* There Should be one View Called `One` so tests can check view filters
  View (name: 'One') - Filter: Where COLUMN_INT == 1
  _____________________________________
 | COLUMN_INT (int) | COLUMN_STR (str) |
  -------------------------------------
 |        1.0       |       '1'        |
   -------------------------------------

"""

filepath = os.path.join('tests', 'mock_responses.json')

responses = {'GET': [],
             'POST': [],
             'DELETE': [],
             'PUT': [],
             'PATCH': []
             }

def _dump_request_data(process_response_func):
    def wrapper(self, response):
        url = response.request.url
        method = response.request.method
        status = response.status_code
        try:
            response_json = response.json()
        except:
            response_json = None
        responses[method].append({'url': url,
                                 'status': status,
                                 'response_json': response_json})

        with open(filepath, 'w') as fp:
            json.dump(responses, fp, indent=2)

        return process_response_func(self, response)
    return wrapper

Airtable._process_response = _dump_request_data(Airtable._process_response)
