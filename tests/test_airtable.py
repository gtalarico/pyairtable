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

    def test_get_records(self, airtable_read):
        records = airtable_read.get_records()
        assert isinstance(records, list)
        assert len(records) == 300

    def test_get_records_view(self, airtable_read):
        records = airtable_read.get_records(view='ViewOne')
        assert len(records) == 1

    def test_get_records_maxrecords(self, airtable_read):
        records = airtable_read.get_records(maxRecords=50)
        assert len(records) == 50

    def test_get_match(self, airtable_read):
        record = airtable_read.get_match('COLUMN_STR', 'DUPLICATE', view='ViewAll')
        assert isinstance(record, dict)
        assert record['fields'].get('COLUMN_ID') == '2'

    def test_get_search(self, airtable_read):
        records = airtable_read.get_search('COLUMN_STR', 'DUPLICATE', view='ViewAll')
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
        resp = airtable_write.insert(row)
        assert resp.ok

    def test_create_batch(self, airtable_write):
        for i in range(5):
            resp = airtable_write.insert(self.row())
            assert resp.ok


class TestAirtableUpdate():

    @pytest.fixture
    def old_field(self):
        return {'COLUMN_UPDATE': 'A'}

    @pytest.fixture
    def new_field(self):
        return {'COLUMN_UPDATE': 'B'}

    def test_update(self, airtable_read, new_field, old_field):
        record = airtable_read.get_records(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

        airtable_read.update(record['id'], new_field)
        record = airtable_read.get_records(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'

        airtable_read.update(record['id'], old_field)
        record = airtable_read.get_records(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

    def test_update_by_field(self, airtable_read, new_field, old_field):
        airtable_read.update_by_field('COLUMN_UPDATE', 'A', new_field)
        record = airtable_read.get_records(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'

        airtable_read.update(record['id'], old_field)
        record = airtable_read.get_records(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

def populate_table_a(self, airtable_write):
    for i in range(4, 300):
        row = {'COLUMN_ID': str(i)}
        resp = airtable_write.insert(row)
        assert resp.ok
