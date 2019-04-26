"""High-level request tests

We don't need to test the requests package it has it's own tests.
All we care about is that we are sending the right arguments,
keyword argument and session data to the correct request method.

We don't need to test the real Airtable responses here either.
If the data is bad it should be caught and discrepencies reported in
the exception handlers when validating the data against the JSON schema.
The API responses are essentially a contract based on the API version.
In otherwords it's the service provider's job to not change the API
response schema without changing the version, and they are responsible
for still maintainng the old API version when a new version is released.
It is possible after a long period of time an API version is deprecated
but that would be caught by exception handling and it's the service
provider's job to provide an error message indicating that the version
is deprecated.

We do need to simulate a response however for multi-page requests so
that we can check that the pagination code is working correctly.

Most of the tests were taken from examples in the documentation or
source code docstrings, including README.md and
https://airtable-python-wrapper.readthedocs.io

Some of the Airtable.get tests are currently marked as skipped because
either the Parameters section of the documentation is incorrect or
there is a bug in the Airtable.get method.  The examples
are missing get's required record argument and they include keyword
arguments which are not part of the Airtable.get method signature.
"""

from collections import OrderedDict, namedtuple
from copy import deepcopy
from unittest.mock import Mock

import pytest

from .test_airtable import air_table as at


Params = namedtuple('Params', ['kwds', 'params'])


def generate_responses(*args, **kwds):
    """Mocks Airtable multi-page responses.

    For example, `get_all` may need to make multiple requests to get
    all pages.  This function simulates the responses.

    * Returns 3 pages containing 2 records each.
    * Page 1 & 2 include an offset key/value along with the records.
    * Page 3 doesn't have an offset key; indicating it's the last page.
    """
    data = {
        "records": [
             {
                "id": "1",
                "fields": {
                    "COLUMN_ID": "1"
                },
                "createdTime": "2017-03-14T22:04:31.000Z"
             }, {
                "id": "2",
                "fields": {
                    "COLUMN_ID": "2"
                },
                "createdTime": "2017-03-20T15:21:50.000Z"
             }
        ],
        "offset": "itr1/rec1"
    }
    responses = [Mock() for i in range(3)]
    for response in responses:
        response.raise_for_status.return_value = False
        response.data = deepcopy(data)
    del responses[-1].data['offset']
    return responses


@pytest.fixture
def air_table(at):
    at.session.request = Mock()
    at.session.request.request_for_status.return_value = None
    return at


@pytest.fixture
def airtable_pages(air_table):
    air_table._process_response = lambda x: x.data
    air_table.session.request.side_effect = generate_responses()
    return air_table


# See https://airtable-python-wrapper.readthedocs.io/en/master/params.html
@pytest.mark.skip(reason="Examples from docs that are not currently supported")
@pytest.mark.get
@pytest.mark.parametrize('kwds,params', [
    Params(
        kwds=dict(fields='ColumnA'),
        params=[('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(fields=['ColumnA', 'ColumnB']),
        params=[('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(sort='ColumnA'),
        params=[('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(sort=['ColumnA', '-ColumnB']),
        params=[('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(sort=[('ColumnA', 'asc'), ('ColumnB', 'desc')]),
        params=[('offset', 'itr1/rec1')]),
])
def test_get_with_options(kwds, params, air_table):
    assert air_table.session.params == {}
    assert vars(air_table.session.auth) == {'api_key': 'API Key'}
    air_table.get(**kwds)
    air_table.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict(params))
    air_table.session.request.assert_called_once()


@pytest.mark.test_get
def test_get(air_table):
    assert air_table.session.params == {}
    assert vars(air_table.session.auth) == {'api_key': 'API Key'}
    air_table.get('recwPQIfs4wKPyc9D')
    air_table.session.request.assert_called_with(
        'get',
        'https://api.airtable.com/v0/Base Key/Table%20Name/recwPQIfs4wKPyc9D',
        json=None, params=OrderedDict())
    air_table.session.request.assert_called_once()


@pytest.mark.get_all
@pytest.mark.parametrize('kwds,params', [
    Params(
        kwds={},
        params=[('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(max_records=10),
        params=[('maxRecords', 10), ('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(view='MyView', maxRecords=20),
        params=[('maxRecords', 20), ('offset', 'itr1/rec1'),
                ('view', 'MyView')]),
    Params(
        kwds=dict(page_size=50),
        params=[('offset', 'itr1/rec1'), ('pageSize', 50)]),
    Params(
        kwds=dict(view='ViewName', sort='COLUMN_A'),
        params=[('offset', 'itr1/rec1'), ('sort[0][direction]', 'asc'),
                ('sort[0][field]', 'COLUMN_A'), ('view', 'ViewName')]),
    Params(
        kwds=dict(formula="FIND('DUP', {COLUMN_STR})=1"),
        params=[('filterByFormula', "FIND('DUP', {COLUMN_STR})=1"),
                ('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(formula="FIND('SomeSubText', {COLUMN_STR})=1"),
        params=[('filterByFormula', "FIND('SomeSubText', {COLUMN_STR})=1"),
                ('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(formula="NOT({COLUMN_A}='')"),
        params=[('filterByFormula', "NOT({COLUMN_A}='')"),
                ('offset', 'itr1/rec1')]),
    Params(
        kwds=dict(view='MyView', fields=['ColA', '-ColB']),
        params=[('fields[]', ['ColA', '-ColB']), ('offset', 'itr1/rec1'),
                ('view', 'MyView')]),
    Params(
        kwds=dict(view='MyView', fields=['ColA', '-ColB']),
        params=[('fields[]', ['ColA', '-ColB']), ('offset', 'itr1/rec1'),
                ('view', 'MyView')]),
    Params(
        kwds=dict(maxRecords=3, view='All'),
        params=[('maxRecords', 3), ('offset', 'itr1/rec1'),
                ('view', 'All')]),
])
def test_get_all(kwds, params, airtable_pages):
    assert airtable_pages.session.params == {}
    assert vars(airtable_pages.session.auth) == {'api_key': 'API Key'}
    records = airtable_pages.get_all(**kwds)
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict(params))
    assert airtable_pages.session.request.call_count == 3
    assert len(records) == 6


@pytest.mark.test_get_iter
def test_get_iter(airtable_pages):
    assert airtable_pages.session.params == {}
    assert vars(airtable_pages.session.auth) == {'api_key': 'API Key'}
    for page in airtable_pages.get_iter(view='ViewName', sort='COLUMN_A'):
        for num, record in enumerate(page, 1):
            assert record['fields']['COLUMN_ID'] == str(num)
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict([
            ('offset', 'itr1/rec1'), ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'COLUMN_A'), ('view', 'ViewName')]))
    assert airtable_pages.session.request.call_count == 3


@pytest.mark.insert
@pytest.mark.parametrize('fields', [
    {'Name': 'Brian'},
    {'First Name': 'John'}
])
def test_insert(fields, air_table):
    air_table.insert(fields)
    assert air_table.session.params == {}
    assert vars(air_table.session.auth) == {'api_key': 'API Key'}
    air_table.session.request.assert_called_with(
        'post', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json={'fields': fields, 'typecast': False}, params=None
    )
    air_table.session.request.assert_called_once()


@pytest.mark.search
@pytest.mark.parametrize('args,params', [
    (
        ['Name', 'Tom'],
        [('filterByFormula', "{Name}='Tom'"), ('offset', 'itr1/rec1')]
    ), (
        ['ColumnA', 'SearchValue'],
        [('filterByFormula', "{ColumnA}='SearchValue'"),
         ('offset', 'itr1/rec1')],
    ), (
        ['Gender', 'Male'],
        [('filterByFormula', "{Gender}='Male'"), ('offset', 'itr1/rec1')]
    )
])
def test_search(args, params, airtable_pages):
    records = airtable_pages.search(*args)
    assert airtable_pages.session.params == {}
    assert vars(airtable_pages.session.auth) == {'api_key': 'API Key'}
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict(params))
    assert airtable_pages.session.request.call_count == 3
    assert len(records) == 6


@pytest.mark.match
@pytest.mark.parametrize('args,params', [
    (
        ['Name', 'John'],
        [('filterByFormula', "{Name}='John'"), ('offset', 'itr1/rec1')]
    ), (
        ['Employee Id', 'DD13332454'],
        [('filterByFormula', "{Employee Id}='DD13332454'"),
         ('offset', 'itr1/rec1')],
    ), (
        ['Seat Number', '22A'],
        [('filterByFormula', "{Seat Number}='22A'"), ('offset', 'itr1/rec1')]
    )
])
def test_match(args, params, airtable_pages):
    airtable_pages.match(*args)
    assert airtable_pages.session.params == {}
    assert vars(airtable_pages.session.auth) == {'api_key': 'API Key'}
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict(params))
    # TODO: why not use get_iter instead of always reading in all pages?
    assert airtable_pages.session.request.call_count == 3


def test_match_returns_first_record_only(air_table):
    assert air_table.session.params == {}
    assert vars(air_table.session.auth) == {'api_key': 'API Key'}
    air_table.session.request.return_value = {"records": []}
    record = air_table.match('COLUMN_ID', '1')
    assert air_table.session.request.assert_called_once()
    assert record == {'fields': {'COLUMN_ID': '1'}}


def test_no_match_found(air_table):
    assert air_table.session.params == {}
    assert vars(air_table.session.auth) == {'api_key': 'API Key'}
    air_table.session.request.return_value = {"records": []}
    record = air_table.match('Name', 'John')
    assert air_table.session.request.assert_called_once()
    assert record == {}


'''
def test_search(air_table):



    airtable.search('Name', 'Tom')
'''
