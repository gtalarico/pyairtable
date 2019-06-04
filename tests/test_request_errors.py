import sys

import pytest
from mock import Mock
from requests import HTTPError
from six.moves import reload_module as reload


import airtable.table
from .test_airtable import air_table


@pytest.fixture
def response():
    response = Mock()
    response.raise_for_status.side_effect = http_error
    response.url = 'page%20url'
    return response


def http_error():
    raise HTTPError('Not Found')


def http_error_with_url():
        raise HTTPError('unable to process page%20url')


def json_decoder_error():
    raise ValueError()



def test_error_mesg_in_json(air_table, response):
    response.status_code = 400
    response.json = Mock(return_value={"error": "here's what went wrong"})
    with pytest.raises(HTTPError) as e:
        air_table._process_response(response)
    assert str(e).endswith("Not Found [Error: here's what went wrong]")



def test_error_without_mesg_in_json(air_table, response):
    response.status_code = 404
    response.json = Mock(return_value={})
    with pytest.raises(HTTPError) as e:
        air_table._process_response(response)
    assert str(e).endswith('Not Found')



def test_404_error_with_json_decode_error(air_table, response):
    response.status_code = 404
    response.json.side_effect = json_decoder_error
    with pytest.raises(HTTPError) as e:
        air_table._process_response(response)
    assert str(e).endswith('Not Found')


def test_422_error_not_ipy(air_table, response):
    sys.implementation.name = Mock()
    sys.implementation.name = 'cpython'
    response.status_code = 422
    response.json.side_effect = json_decoder_error
    response.raise_for_status.side_effect = http_error_with_url
    with pytest.raises(HTTPError) as e:
        air_table._process_response(response)
    assert str(e).endswith('unable to process page url (Decoded URL)')


def test_422_error_using_ipy(air_table, response):
    sys.implementation.name = Mock()
    sys.implementation.name = 'ironpython'
    reload(airtable.table)
    assert airtable.table.IS_IPY
    response.status_code = 422
    response.json.side_effect = json_decoder_error
    response.raise_for_status.side_effect = http_error_with_url
    with pytest.raises(HTTPError) as e:
        air_table._process_response(response)
    assert str(e).endswith('unable to process page%20url')
    sys.implementation.name = 'cpython'
    reload(airtable.table)


def test_not_422_error_using_ipy(air_table, response):
    sys.implementation.name = Mock()
    sys.implementation.name = 'ironpython'
    reload(airtable.table)
    assert airtable.table.IS_IPY
    response.status_code = 404
    response.json.side_effect = json_decoder_error
    response.raise_for_status.side_effect = http_error_with_url
    with pytest.raises(HTTPError) as e:
        air_table._process_response(response)
    assert str(e).endswith('unable to process page%20url')
    sys.implementation.name = 'cpython'
    reload(airtable.table)
