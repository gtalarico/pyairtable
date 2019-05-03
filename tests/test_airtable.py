import os
import sys
from importlib import reload
from unittest.mock import Mock

import pytest
import airtable
from airtable.airtable import Airtable

Airtable.VERSION = 'v0'
Airtable.API_BASE_URL = 'https://api.airtable.com/'
Airtable.API_LIMIT = 0

API_KEY_ENV_NAME = 'AIRTABLE_API_KEY'

BASE_KEY = 'Base Key'
TABLE_NAME = 'Table Name'
API_KEY = 'API Key'


@pytest.fixture
def air_table():
    return Airtable(BASE_KEY, TABLE_NAME, API_KEY, validate_session=False)


@pytest.mark.url
def test_airtable_api_url_creation():
    assert Airtable.API_URL == 'https://api.airtable.com/v0'


@pytest.mark.url
def test_airtable_table_url_creation(air_table):
    expected_url = 'https://api.airtable.com/v0/Base Key/Table%20Name'
    assert air_table.url_table == expected_url


@pytest.mark.url
def test_airtable_record_url_creation(air_table):
    expected_url = (
        'https://api.airtable.com/v0/Base Key/Table%20Name/recAXYw8GsVCG1JKp'
    )
    assert air_table.record_url('recAXYw8GsVCG1JKp') == expected_url


@pytest.mark.validate
def test_airtable_valid_session(air_table):
    response = Mock(ok=True, status_code=200)
    air_table.session.get = Mock(return_value=response)
    assert air_table.validate_session(air_table.url_table) is True


@pytest.mark.validate
def test_airtable_invalid_sessions(air_table):
    response = Mock(ok=False)
    # if the table name is not valid it will return a 404 code.
    for response.status_code in [404, 400]:
        air_table.session.get = Mock(return_value=response)
        with pytest.raises(ValueError):
            air_table.validate_session(air_table.url_table)


def test_ipy():
    sys.implementation.name = Mock()
    sys.implementation.name = 'cpython'
    reload(airtable.airtable)
    assert not airtable.airtable.IS_IPY
    sys.implementation.name = 'ironpython'
    reload(airtable.airtable)
    assert airtable.airtable.IS_IPY
    sys.implementation = Mock(spec=[], cache_tag='cpython')
    reload(airtable.airtable)
    assert not airtable.airtable.IS_IPY


def test_process_response(air_table):
    response = Mock()
    response.raise_for_status = Mock(return_value=None)
    response.json = Mock(return_value='{}')
    result = air_table._process_response(response)
    assert result == '{}'
    # TODO: HTTPError processing
