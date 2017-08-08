from __future__ import absolute_import

import pytest
import requests
import uuid

from airtable import Airtable
from airtable.auth import AirtableAuth

TEST_BASE_KEY = 'appJMY16gZDQrMWpA'
TEST_TABLE_A = 'TABLE READ'
TEST_TABLE_B = 'TABLE WRITE'

"""
=======
TABLE A
=======

ViewAll
----------------------
COLUMN_ID | COLUMN_STR
    1           A
    2           B
    3           C

ViewOne (COLUMN_ID == 1)
----------------------
COLUMN_ID | COLUMN_STR
    1           A

=======
TABLE B
=======

"""

@pytest.fixture(scope='session')
def airtable_read():
    airtable = Airtable(TEST_BASE_KEY, TEST_TABLE_A)
    assert airtable.is_authenticated is True
    return airtable

@pytest.fixture(scope='session')
def airtable_write():
    airtable = Airtable(TEST_BASE_KEY, TEST_TABLE_B)
    assert airtable.is_authenticated is True
    return airtable


class TestAuth():

    def test_authorization_scheme(self):
        session = requests.Session()
        session.auth = AirtableAuth()
        resp = session.get('http://www.google.com')
        assert 'Authorization' in resp.request.headers
        assert 'Bearer' in resp.request.headers['Authorization']

    def test_authorization_call(self):
        session = requests.Session()
        auth = AirtableAuth()
        session = auth.__call__(session)
        assert 'Authorization' in session.headers
        assert 'Bearer' in session.headers['Authorization']

    def test_authorization_is(self, airtable_read):
        assert airtable_read.is_authenticated

class TestAirtableGet():

    def test_get(self, airtable_read):
        for n, records in enumerate(airtable_read.get(view='ViewAll'), 1):
            assert isinstance(records, list)
            assert len(records) == 100
            assert records[0]['fields']['COLUMN_ID'] in ['1', '101', '201']

    def test_get_all(self, airtable_read):
        records = airtable_read.get_all()
        assert isinstance(records, list)
        assert len(records) == 300

    def test_get_pagesize(self, airtable_read):
        for records in airtable_read.get(pageSize=60):
            assert len(records) == 60
            break

    def test_get_all_view(self, airtable_read):
        records = airtable_read.get_all(view='ViewOne')
        assert len(records) == 1

    @pytest.mark.skip(reason="not implemented")
    def test_get_fields(self, airtable_read):
        record = airtable_read.get_all(fields=['COLUMN_STR'], maxRecords=1)[0]
        assert 'COLUMN_ID' in record['fields']
        assert 'COLUMN_STR' in record['fields']
        assert 'COLUMN_UPDATE' not in record

    def test_get_all_maxrecords(self, airtable_read):
        records = airtable_read.get_all(maxRecords=50)
        assert len(records) == 50

    def test_match(self, airtable_read):
        record = airtable_read.match('COLUMN_STR', 'DUPLICATE', view='ViewAll')
        assert isinstance(record, dict)
        assert record['fields'].get('COLUMN_ID') == '2'

    def test_search(self, airtable_read):
        records = airtable_read.search('COLUMN_STR', 'DUPLICATE', view='ViewAll')
        assert isinstance(records, list)
        assert len(records) == 2
        assert records[0]['fields'].get('COLUMN_ID') == '2'
        assert records[1]['fields'].get('COLUMN_ID') == '3'
        assert all([True for r in records if r['fields']['COLUMN_STR'] == 'DUPLICATE'])


class TestAirtableCreate():

    @pytest.fixture
    def row(self):
        return  {'UUID': str(uuid.uuid4()), 'String': 'TestAirTableCreate'}

    def test_create_one(self, row, airtable_write):
        response = airtable_write.insert(row)
        assert 'id' in response

    def test_create_batch(self, airtable_write):
        for i in range(5):
            response = airtable_write.insert(self.row())
            assert 'id' in response


class TestAirtableUpdate():

    @pytest.fixture
    def old_field(self):
        return {'COLUMN_UPDATE': 'A'}

    @pytest.fixture
    def new_field(self):
        return {'COLUMN_UPDATE': 'B'}

    def test_update(self, airtable_read, new_field, old_field):
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

        airtable_read.update(record['id'], new_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'

        airtable_read.update(record['id'], old_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

    def test_update_by_field(self, airtable_read, new_field, old_field):
        airtable_read.update_by_field('COLUMN_UPDATE', 'A', new_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'

        airtable_read.update(record['id'], old_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'


class TestAirtableDelete():

    @pytest.fixture
    def row(self):
        return  {'UUID': '4e8f9cfa-543b-492f-962b-e16930b49cae', 'String': 'Deleted Test'}

    def test_delete(self, airtable_write, row):
        record = airtable_write.match('UUID', row['UUID'])
        response = airtable_write.delete(record['id'])

        assert response.get('deleted') is True
        assert 'id' in response
        airtable_write.insert(row)

def populate_table_a(self, airtable_write):
    for i in range(4, 300):
        row = {'COLUMN_ID': str(i)}
        resp = airtable_write.insert(row)
        assert resp.ok
