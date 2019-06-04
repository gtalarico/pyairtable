"""High-level HTTP request tests.

We don't need to test the requests package it has it's own set of tests.
All we care about is that we are sending exactly the right arguments,
keyword options and session data to the correct request method.

However, we do need to simulate a response for multi-page requests to
check that the pagination code is working correctly.

We also don't need to test the real Airtable responses here either,
that's dealt with through schema validation and exception handling.
The API responses are essentially a contract based on the API version.
In otherwords it's the service provider's job to not change the API
response schema without bumping the version, and they are responsible
for still maintainng the old API version when a new version is released.
It is possible after a long period of time an API version is deprecated
but that would be caught by exception handling and it's the service
provider's job to provide an error message indicating that the version
is deprecated.

Most of the tests were taken from examples in the docs, docstrings,
and README file.

Some of the Airtable.get tests are currently marked as skipped because
either the Parameters section of the documentation is incorrect or
there is a bug in the Airtable.get method.  The examples
are missing get's required record argument and they include keyword
arguments which are not part of the Airtable.get method signature.
"""

from collections import OrderedDict, namedtuple
from copy import deepcopy

import pytest
from mock import Mock

import airtable.table as table
from .test_airtable import air_table as at
from .test_airtable import Airtable

Params = namedtuple('Params', ['kwds', 'params'])
HEADER_BASE_PARAMS = {'User-Agent', 'Accept-Encoding', 'Accept', 'Connection'}

TEST_DATA = {
    "records": [
        {
            "id": "1",
            "fields": {
                "Name": "John",
                "Phone": "2468-5790",
                "State": "CA"
            },
            "createdTime": "2017-03-14T22:04:31.000Z"
        }, {
            "id": "2",
            "fields": {
                "Name": "Tom",
                "Phone": "1234-9876",
                "State": "FL"
            },
            "createdTime": "2017-03-20T15:21:50.000Z"
        }
    ],
    "offset": "itr1/rec1"
}


def generate_responses(*args, **kwds):
    """Mocks Airtable multi-page responses.

    For example, `get_all` may need to make multiple requests to get
    all pages.  This function simulates the responses.

    * Returns 3 pages containing 2 records each.
    * Page 1 & 2 include an offset key/value along with the records.
    * Page 3 doesn't have an offset key; indicating it's the last page.
    """
    responses = [Mock(name='response') for i in range(3)]
    for response in responses:
        response.raise_for_status.return_value = False
        response.data = deepcopy(TEST_DATA)
    del responses[-1].data['offset']
    return responses


def match(name, value, *args, **kwds):
    for record in TEST_DATA['records']:
        if record['fields'][name] == value:
            return record


@pytest.fixture
def air_table(at):

    # make sure we are starting with a pristine session and that what
    # we are testing is the full complement of what is being sent in
    # the request
    assert at.session.params == {}
    assert set(at.session.headers) == HEADER_BASE_PARAMS
    assert vars(at.session.auth) == {'api_key': 'API Key'}

    at.session.request = Mock(name='request')
    at.session.request.request_for_status.return_value = None
    yield at

    # make sure the session didn't change somewhere along the way and
    # send additional untested information
    assert at.session.params == {}
    assert set(at.session.headers) == HEADER_BASE_PARAMS
    assert vars(at.session.auth) == {'api_key': 'API Key'}


@pytest.fixture
def airtable_pages(air_table):
    air_table._process_response = lambda x: x.data
    air_table.session.request.side_effect = generate_responses()
    return air_table


# --- CREATE RECORDS ---


@pytest.mark.create
@pytest.mark.parametrize('fields', [
    {'Name': 'Brian'},
    {'First Name': 'John'}
])
def test_insert(fields, air_table):
    air_table.insert(fields)
    air_table.session.request.assert_called_with(
        'post',
        'https://api.airtable.com/v0/Base Key/Table%20Name',
        json={
            'fields': fields,
            'typecast': False
        },
        params=None
    )
    air_table.session.request.assert_called_once()


@pytest.mark.create
def test_batch_insert(air_table):
    air_table.batch_insert([{'Name': 'John'}, {'Name': 'Marc'}])
    air_table.session.request.any_call(
        'post',
        'https://api.airtable.com/v0/Base Key/Table%20Name',
        json={
            'fields': {
                'Name': 'John'
            },
            'typecast': False
        },
        params=None
    )
    air_table.session.request.any_call(
        'post',
        'https://api.airtable.com/v0/Base Key/Table%20Name',
        json={
            'fields': {
                'Name': 'Marc'
            },
            'typecast': False
        },
        params=None
    )
    air_table.session.request.call_count == 2


@pytest.mark.mirror
def test_mirror(airtable_pages):
    # destructive creation: batch_delete followed by a batch_insert
    records = [{'Name': 'John'}, {'Name': 'Marc'}]
    airtable_pages.batch_delete = Mock()
    airtable_pages.batch_insert = Mock()
    airtable_pages.mirror(records)
    airtable_pages.session.request.assert_called_with(
        'get',
        'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None,
        params=OrderedDict([('offset', 'itr1/rec1')])
    )
    assert airtable_pages.session.request.call_count == 3
    airtable_pages.batch_delete.assert_called_with(
        ['1', '2', '1', '2', '1', '2']
    )
    airtable_pages.batch_insert.assert_called_with(records)


# --- READ RECORDS ---


@pytest.mark.read
def test_get(air_table):
    air_table.get('recwPQIfs4wKPyc9D')
    air_table.session.request.assert_called_with(
        'get',
        'https://api.airtable.com/v0/Base Key/Table%20Name/recwPQIfs4wKPyc9D',
        json=None,
        params=OrderedDict()
    )
    air_table.session.request.assert_called_once()


# See https://airtable-python-wrapper.readthedocs.io/en/master/params.html
@pytest.mark.skip(reason="Examples from docs that are not currently supported")
@pytest.mark.get
@pytest.mark.parametrize('kwds,params', [
    Params(
        kwds=dict(
            fields='ColumnA'
        ),
        params=[
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            fields=['ColumnA', 'ColumnB']
        ),
        params=[
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            sort='ColumnA'
        ),
        params=[
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            sort=['ColumnA', '-ColumnB']
        ),
        params=[
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            sort=[
                ('ColumnA', 'asc'),
                ('ColumnB', 'desc')
            ]
        ),
        params=[
            ('offset', 'itr1/rec1')
        ]
    )
])
def test_get_with_options(kwds, params, air_table):
    air_table.get(**kwds)
    air_table.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None,
        params=OrderedDict(params)
    )
    air_table.session.request.assert_called_once()


@pytest.mark.read
@pytest.mark.parametrize('kwds,params', [
    Params(
        kwds={},
        params=[
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            max_records=10
        ),
        params=[
            ('maxRecords', 10),
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            page_size=50
        ),
        params=[
            ('offset', 'itr1/rec1'),
            ('pageSize', 50)
        ]
    ),
    Params(
        kwds=dict(
            view='MyView',
            maxRecords=20),
        params=[
            ('maxRecords', 20),
            ('offset', 'itr1/rec1'),
            ('view', 'MyView')
        ]
    ),
    Params(
        kwds=dict(view='ViewName', sort='COLUMN_A'),
        params=[
            ('offset', 'itr1/rec1'),
            ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'COLUMN_A'),
            ('view', 'ViewName')
        ]
    ),
    Params(
        kwds=dict(
            formula="FIND('DUP', {COLUMN_STR})=1"
        ),
        params=[
            ('filterByFormula', "FIND('DUP', {COLUMN_STR})=1"),
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            formula="FIND('SomeSubText', {COLUMN_STR})=1"
        ),
        params=[
            ('filterByFormula', "FIND('SomeSubText', {COLUMN_STR})=1"),
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            formula="NOT({COLUMN_A}='')"
        ),
        params=[
            ('filterByFormula', "NOT({COLUMN_A}='')"),
            ('offset', 'itr1/rec1')
        ]
    ),
    Params(
        kwds=dict(
            view='MyView',
            fields=['ColA', '-ColB']
        ),
        params=[
            ('fields[]', ['ColA', '-ColB']),
            ('offset', 'itr1/rec1'),
            ('view', 'MyView')
        ]
    ),
    Params(
        kwds=dict(
            view='MyView',
            fields=['ColA', '-ColB']
        ),
        params=[
            ('fields[]', ['ColA', '-ColB']),
            ('offset', 'itr1/rec1'),
            ('view', 'MyView')
        ]
    ),
    Params(
        kwds=dict(
            maxRecords=3,
            view='All'
        ),
        params=[('maxRecords', 3), ('offset', 'itr1/rec1'),
                ('view', 'All')]),
])
def test_get_all(kwds, params, airtable_pages):
    records = airtable_pages.get_all(**kwds)
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None,
        params=OrderedDict(params)
    )
    assert airtable_pages.session.request.call_count == 3
    assert len(records) == 6


@pytest.mark.read
@pytest.mark.parametrize('rate', [0, 0.2])
def test_get_all_rate_limit(rate, airtable_pages):
    Airtable.API_LIMIT = rate
    table.time.sleep = Mock()
    airtable_pages.get_all()
    table.time.sleep.assert_called_with(rate)
    assert table.time.sleep.call_count == 3
    Airtable.API_LIMIT = 0


@pytest.mark.read
def test_get_iter(airtable_pages):
    for page in airtable_pages.get_iter(view='ViewName', sort='COLUMN_A'):
        for num, record in enumerate(page, 1):
            assert 'Name' in record['fields']
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict([
            ('offset', 'itr1/rec1'),
            ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'COLUMN_A'),
            ('view', 'ViewName')
        ])
    )
    assert airtable_pages.session.request.call_count == 3


# --- UPDATE RECORDS ---


@pytest.mark.update
@pytest.mark.parametrize('fields', [{'Status': 'Fired'}])
def test_update(fields, air_table):
    air_table.update('recwPQIfs4wKPyc9D', fields)
    air_table.session.request.assert_called_with(
        'patch',
        'https://api.airtable.com/v0/Base Key/Table%20Name/recwPQIfs4wKPyc9D',
        json={'fields': {'Status': 'Fired'}, 'typecast': False},
        params=None
    )
    air_table.session.request.assert_called_once()


@pytest.mark.update
@pytest.mark.parametrize('field_name,field_value,fields,record_id', [
    ('Name', 'Tom', {'Phone': '1234-4445'}, '2'),
    ('Name', 'John', {'Name': 'Johnny', 'Tel': '540-255-5522'}, '1'),
    ('Name', 'Joe', {'Phone': '1234-4445'}, None),
])
def test_update_by_field(
    field_name, field_value, fields, record_id, airtable_pages
):
    airtable_pages.match = Mock(side_effect=match)
    result = airtable_pages.update_by_field(field_name, field_value, fields)
    assert airtable_pages.match.called_with(field_name, field_value)
    assert airtable_pages.match.called_once()
    if record_id:
        airtable_pages.session.request.assert_called_with(
            'patch',
            'https://api.airtable.com/v0/Base Key/Table%20Name/' + record_id,
            json={'fields': fields, 'typecast': False},
            params=None
        )
    else:
        airtable_pages.session.request.assert_not_called()
        assert result == {}


@pytest.mark.update
def test_replace(air_table):
    fields = {'Name': 'Billy'}
    air_table.replace('recwPQIfs4wKPyc9D', fields)
    air_table.session.request.assert_called_with(
        'put',
        'https://api.airtable.com/v0/Base Key/Table%20Name/recwPQIfs4wKPyc9D',
        json={'fields': fields, 'typecast': False},
        params=None
    )


@pytest.mark.update
def test_replace_by_field(airtable_pages):
    airtable_pages.match = Mock(side_effect=match)
    field_name = 'Name'
    field_value = 'Tom'
    record_id = '2'
    fields = {'Name': 'Billy'}
    result = airtable_pages.replace_by_field(field_name, field_value, fields)
    assert airtable_pages.match.called_with(field_name, field_value)
    if record_id:
        airtable_pages.session.request.assert_called_with(
            'put',
            'https://api.airtable.com/v0/Base Key/Table%20Name/' + record_id,
            json={'fields': fields, 'typecast': False},
            params=None
        )
    else:
        airtable_pages.session.request.assert_not_called()
        assert result == {}


# --- DELETE RECORDS ---


@pytest.mark.delete
def test_delete(air_table):
    air_table.delete('recwPQIfs4wKPyc9D')
    air_table.session.request.assert_called_with(
        'delete',
        'https://api.airtable.com/v0/Base Key/Table%20Name/recwPQIfs4wKPyc9D',
        json=None,
        params=None
    )
    air_table.session.request.assert_called_once()


@pytest.mark.delete
def test_batch_delete(air_table):
    record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
    air_table.batch_delete(record_ids)
    air_table.session.request.any_call(
        'delete',
        'https://api.airtable.com/v0/Base Key/Table%20Name/recwPQIfs4wKPyc9D',
        json=None,
        params=None
    )
    air_table.session.request.any_call(
        'delete',
        'https://api.airtable.com/v0/Base Key/Table%20Name/recwDxIfs3wDPyc3F',
        json=None,
        params=None
    )


@pytest.mark.delete
@pytest.mark.parametrize(
    'field_name,field_value,record_id', [
        ('Name', 'Tom', '2'),
        ('Name', 'John', '1')
    ]
)
def test_delete_by_field(field_name, field_value, record_id, airtable_pages):
    # TODO: delete_by_field should behave the same as update_by_field
    # when field/value match is not found.  update_by_field contains
    # logic to handle this, delete_by_field does not
    # once working add ('Name', 'Joe', None) to the parmaeters.
    airtable_pages.match = Mock(side_effect=match)
    result = airtable_pages.delete_by_field(field_name, field_value)
    assert airtable_pages.match.called_with(field_name, field_value)
    assert airtable_pages.match.called_once()
    if record_id:
        airtable_pages.session.request.assert_called_with(
            'delete',
            'https://api.airtable.com/v0/Base Key/Table%20Name/' + record_id,
            json=None,
            params=None
        )
        airtable_pages.session.request.assert_called_once()
    else:
        airtable_pages.session.request.assert_not_called()
        assert result == {}


# --- SEARCH RECORDS ---


@pytest.mark.search
@pytest.mark.parametrize(
    'args,params', [
        (
            ['Name', 'Tom'],
            [
                ('filterByFormula', "{Name}='Tom'"),
                ('offset', 'itr1/rec1')
            ]
        ),
        (
            ['ColumnA', 'SearchValue'],
            [
                ('filterByFormula', "{ColumnA}='SearchValue'"),
                ('offset', 'itr1/rec1')
            ],
        ),
        (
            ['Gender', 'Male'],
            [
                ('filterByFormula', "{Gender}='Male'"),
                ('offset', 'itr1/rec1')
            ]
        )
    ]
)
def test_search(args, params, airtable_pages):
    records = airtable_pages.search(*args)
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict(params))
    assert airtable_pages.session.request.call_count == 3
    assert len(records) == 6


@pytest.mark.search
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
    airtable_pages.session.request.assert_called_with(
        'get', 'https://api.airtable.com/v0/Base Key/Table%20Name',
        json=None, params=OrderedDict(params))
    # TODO: why not use get_iter instead of always reading in all pages?
    assert airtable_pages.session.request.call_count == 3


@pytest.mark.search
def test_match_empty_table(airtable_pages):
    airtable_pages.get_all = Mock(return_value=[])
    result = airtable_pages.match('Name', 'John')
    assert result == {}