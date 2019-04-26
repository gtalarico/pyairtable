import pytest
import json
from collections import OrderedDict
from posixpath import join as urljoin
from six.moves.urllib.parse import urlencode, quote
from requests_mock import Mocker

from airtable import Airtable

TABLE_NAME = 'FakeTable'
BASE_KEY = 'appFakeBaseKey'
API_KEY = 'FAKE_API_KEY'


with open('tests/mock_responses.json') as fp:
    RESPONSES = json.load(fp)


def get_response(method, url, status_code):
    responses = RESPONSES[method]
    for r in responses:
        if r['url'] == url and r['status'] == status_code:
            return r
    else:
        raise Exception('Could not find mock response match')


@pytest.fixture()
def mock_airtable():
    mock_url = build_url(params={'maxRecords': 1})
    with Mocker() as m:
        m.get(mock_url, status_code=200)
        airtable = Airtable(BASE_KEY, TABLE_NAME, api_key=API_KEY)
    return airtable


def build_url(*args, params=None):
    """ Builds Airtable Api Url Manually for mock testing """
    url = urljoin(Airtable.API_URL, BASE_KEY, TABLE_NAME)

    if args:
       url = urljoin(url, *args)

    if params:
        params = OrderedDict(sorted(params.items()))
        url += '?' + urlencode(params)

    return url


class TestAirable():


    def test_get_record(self, mock_airtable):
        record_id = 'rec0LQoJ4Vgp8fPty'  # From Dumped Response
        status = 200
        mock_url = build_url(record_id)
        json_response = get_response('GET', mock_url, status)['json']

        with Mocker() as m:
            m.get(mock_url, status_code=status, json=json_response)
            resp = mock_airtable.get(record_id)
        assert resp['id'] == record_id

    def test_get_iter(self, mock_airtable):
        status = 200
        mock_url = build_url()
        json_response = get_response('GET', mock_url, status)['json']

        with Mocker() as m:
            m.get(mock_url, status_code=status, json=json_response)
            for resp in mock_airtable.get_iter():
                import pdb; pdb.set_trace()
                # MUST USE FUZZY MATCH BECAUSE RECORDS IS NOT AVAILABLE
                mock_url = build_url(params={'offset': resp['offset']})
                m.get(mock_url, status_code=status, json=json_response)
                assert 'offset' in resp
                json_response = get_response('GET', mock_url, status)['json']
                assert 'records' in json_response


