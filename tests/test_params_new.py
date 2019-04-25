from collections import OrderedDict

import pytest

from .test_airtable_new import air_table

PARAMS = [
    ({'view': 'SomeView'}, OrderedDict([('view', 'SomeView')])),
    ({'max_records': 5}, OrderedDict([('maxRecords', 5)])),
    ({'maxRecords': 5}, OrderedDict([('maxRecords', 5)])),
    ({'page_size': 5}, OrderedDict([('pageSize', 5)])),
    ({'pageSize': 5}, OrderedDict([('pageSize', 5)])),
    ({'formula': 'NOT(1)'}, OrderedDict([('filterByFormula', 'NOT(1)')])),
    ({'fields': 'Name'}, OrderedDict([('fields[]', 'Name')])),
    ({'fields': ['Name']}, OrderedDict([('fields[]', ['Name'])])),
    (
        {'fields': ['Name', 'Phone']},
        OrderedDict([
            ('fields[]', ['Name', 'Phone'])
        ])
    ), (
        {'filterByFormula': 'NOT(1)'},
        OrderedDict([
            ('filterByFormula', 'NOT(1)')
        ])
    ), (
        {'formula': 'AND({COLUMN_ID}<=6, {COLUMN_ID}>3)'},
        OrderedDict([
            ('filterByFormula', 'AND({COLUMN_ID}<=6, {COLUMN_ID}>3)')
        ])
    ), (
        {'sort': 'Name'},
        OrderedDict([
            ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'Name')
        ])
    ), (
        {'sort': ['Name']},
        OrderedDict([
            ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'Name')
        ])
    ), (
        {'sort': ['Name', 'Phone']},
        OrderedDict([
            ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'Name'),
            ('sort[1][direction]', 'asc'),
            ('sort[1][field]', 'Phone')
        ])
    ), (
        {'sort': ['Name', '-Phone']},
        OrderedDict([
            ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'Name'),
            ('sort[1][direction]', 'desc'),
            ('sort[1][field]', 'Phone')
        ])
    ), (
        {'sort': [('Name', 'desc'), ('Phone', 'asc')]},
        OrderedDict([
            ('sort[0][direction]', 'desc'),
            ('sort[0][field]', 'Name'),
            ('sort[1][direction]', 'asc'),
            ('sort[1][field]', 'Phone')
        ])
    ), (
        {'max_records': 1, 'view': 'View', 'sort': 'Name'},
        OrderedDict([
            ('maxRecords', 1),
            ('sort[0][direction]', 'asc'),
            ('sort[0][field]', 'Name'),
            ('view', 'View')
        ])
    )
]


@pytest.mark.parametrize('given,expected', PARAMS)
def test_params(given, expected, air_table):
    assert air_table._process_params(given) == expected
