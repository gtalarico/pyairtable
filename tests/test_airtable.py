import pytest
import requests
import uuid

from airtable import Airtable
from airtable.auth import AirtableAuth

TEST_BASE_KEY = 'appJMY16gZDQrMWpA'
TEST_TABLE_A = 'TABLE A'
TEST_TABLE_B = 'TABLE B'
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


class TestAuth():

    def test_authorization_scheme(self):
        session = requests.Session()
        session.auth = AirtableAuth()
        resp = session.get('http://www.google.com')
        assert 'Authorization' in resp.request.headers
        assert 'Bearer' in resp.request.headers['Authorization']


class TestAirtableGet():

    @pytest.fixture(scope='module')
    def airtable(self):
        airtable = Airtable(TEST_BASE_KEY, TEST_TABLE_A)
        assert airtable.is_authenticated is True
        return airtable

    def test_get_all(self, airtable):
        records = airtable.get_all()
        assert isinstance(records, list)
        assert len(records) == 300

    def test_get_all_view(self, airtable):
        records = airtable.get_all(view='ViewOne')
        assert len(records) == 1

    def test_get_all_maxrecords(self, airtable):
        records = airtable.get_all(maxRecords=50)
        assert len(records) == 50

    def test_get_match(self, airtable):
        record = airtable.get_match('COLUMN_STR', 'DUPLICATE')
        assert isinstance(record, dict)
        assert record.get('COLUMN_ID') in ['2', '3']

    def test_get_search(self, airtable):
        records = airtable.get_search('COLUMN_STR', 'DUPLICATE')
        assert isinstance(records, list)
        assert len(records) == 2
        assert records[0].get('COLUMN_ID') in ['2', '3']
        assert records[1].get('COLUMN_ID') in ['2', '3']
        assert all([True for r in records if r['COLUMN_STR'] == 'DUPLICATE'])


class TestAirtableCreate():

    @pytest.fixture
    def row(self):
        return  {'UUID': str(uuid.uuid4()), 'String': 'TestAirTableCreate'}

    @pytest.fixture(scope='module')
    def airtable(self):
        airtable = Airtable(TEST_BASE_KEY, TEST_TABLE_B)
        assert airtable.is_authenticated is True
        return airtable

    def test_create_one(self, row, airtable):
        resp = airtable.insert(row)
        assert resp.ok

    def test_create_batch(self, airtable):
        for i in range(5):
            resp = airtable.insert(self.row())
            assert resp.ok



class TestAirtableUpdate():

    @pytest.fixture(scope='module')
    def airtable(self):
        airtable = Airtable(TEST_BASE_KEY, TEST_TABLE_A)
        assert airtable.is_authenticated is True
        return airtable

    def test_get_all(self, airtable):
        records = airtable.get_all()
        assert isinstance(records, list)
        assert len(records) == 300

    def test_get_all_view(self, airtable):
        records = airtable.get_all(view='ViewOne')
        assert len(records) == 1

    def test_get_all_maxrecords(self, airtable):
        records = airtable.get_all(maxRecords=50)
        assert len(records) == 50


def populate_table_a(self, airtable):
    for i in range(4, 300):
        row = {'COLUMN_ID': str(i)}
        resp = airtable.insert(row)
        assert resp.ok
