from __future__ import absolute_import

import pytest
import os
import requests
import uuid
from requests.exceptions import HTTPError

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


class TestAbout():

    def test_get_about_info(self):
        from airtable.__version__ import (__version__,
                                          __name__,
                                          __description__,
                                          __url__,
                                          __author__,
                                          __license__,
                                          __copyright__,
                                          )
        assert __version__

class TestAuth():

    def test_authorization_scheme(self):
        session = requests.Session()
        session.auth = AirtableAuth()
        resp = session.get('http://www.google.com')
        assert 'Authorization' in resp.request.headers
        assert 'Bearer' in resp.request.headers['Authorization']

    def test_authorization_manual_call(self):
        session = requests.Session()
        auth = AirtableAuth()
        session = auth.__call__(session)
        assert 'Authorization' in session.headers
        assert 'Bearer' in session.headers['Authorization']

    def test_authorization_missing(self):
        key = os.environ.pop('AIRTABLE_API_KEY')
        session = requests.Session()
        with pytest.raises(KeyError):
            session.auth = AirtableAuth()
        os.environ['AIRTABLE_API_KEY'] = key

    def test_authorization_manual_key(self):
        key = os.environ['AIRTABLE_API_KEY']
        session = requests.Session()
        session.auth = AirtableAuth(api_key=key)
        resp = session.get('http://www.google.com')
        assert 'Authorization' in resp.request.headers
        assert 'Bearer' in resp.request.headers['Authorization']

    def test_authorization_is(self, airtable_read):
        assert airtable_read.is_authenticated

    def test_authorization_fail(self, ):
        with pytest.raises(ValueError) as excinfo:
            # Raises Invalid Table Name
            fake_airtable = Airtable(base_key='XXX', table_name='YYY')
            assert 'invalid table' in str(excinfo.value).lower()

    def test_authorization_bad_credentials(self, ):
        with pytest.raises(ValueError) as excinfo:
            # Raises Invalid Table Name
            fake_airtable = Airtable(base_key=TEST_BASE_KEY,
                                     table_name=TEST_TABLE_A,
                                     api_key='BADKEY')
            assert 'authentication failed' in str(excinfo.value).lower()


class TestAirtableGet():

    def test_repr(self, airtable_read):
        assert '<Airtable' in airtable_read.__repr__()
        assert airtable_read.table_name in airtable_read.__repr__()

    def test_get(self, airtable_read):
        record = airtable_read.get('recwPQIfs4wKPyc9D')
        assert isinstance(record, dict)
        assert record['id'] == 'recwPQIfs4wKPyc9D'

    def test_get_iter(self, airtable_read):
        for n, records in enumerate(airtable_read.get_iter(view='ViewAll'), 1):
            assert isinstance(records, list)
            assert len(records) == 100
            assert records[0]['fields']['COLUMN_ID'] in ['1', '101', '201']

    def test_get_all(self, airtable_read):
        records = airtable_read.get_all()
        assert isinstance(records, list)
        assert len(records) == 300

    def test_get_pagesize(self, airtable_read):
        for records in airtable_read.get_iter(pageSize=60):
            assert len(records) == 60
            break

    def test_get_all_view(self, airtable_read):
        records = airtable_read.get_all(view='ViewOne')
        assert len(records) == 1

    def test_get_bad_param(self, airtable_read):
        with pytest.raises(ValueError) as excinfo:
            airtable_read.get_all(view='ViewOne', bad_param=True)
            assert 'invalid param keyword' in str(excinfo.value).lower()

    def test_get_bad_request_decoded_msg(self, airtable_read):
        with pytest.raises(HTTPError) as excinfo:
            airtable_read.get_all(view='ViewOne', sort=['NON_EXISTING'], fields=['X'])
            assert 'Unprocessable Entity for url(decoded)' in str(excinfo.value).lower()
            assert 'sort[0]' in str(excinfo.value).lower()
            assert 'fields[]=' in str(excinfo.value).lower()

    def test_get_all_fields_single(self, airtable_read):
        records = airtable_read.get_all(view='ViewAll', maxRecords=1,
                                        fields=['COLUMN_UPDATE'])
        assert 'COLUMN_ID' not in records[0]['fields']
        assert 'COLUMN_STR' not in records[0]['fields']
        assert 'COLUMN_UPDATE' in records[0]['fields']

    def test_get_all_fields_multiple(self, airtable_read):
        records = airtable_read.get_all(view='ViewAll', maxRecords=1,
                                        fields=['COLUMN_UPDATE', 'COLUMN_ID'])
        assert 'COLUMN_ID' in records[0]['fields']
        assert 'COLUMN_UPDATE' in records[0]['fields']
        assert 'COLUMN_STR' not in records[0]['fields']

    def test_get_all_maxrecords(self, airtable_read):
        records = airtable_read.get_all(maxRecords=50)
        assert len(records) == 50

    def test_get_all_sort_asc(self, airtable_read):
        records = airtable_read.get_all(maxRecords=5, sort=['COLUMN_ID'])
        assert records[0]['fields']['COLUMN_ID'] == '1'
        assert records[2]['fields']['COLUMN_ID'] == '3'

    def test_get_all_sort_asc_str(self, airtable_read):
        records = airtable_read.get_all(maxRecords=5, sort='COLUMN_ID')
        assert records[0]['fields']['COLUMN_ID'] == '1'
        assert records[2]['fields']['COLUMN_ID'] == '3'

    def test_get_all_sort_desc(self, airtable_read):
        records = airtable_read.get_all(maxRecords=5, sort=['-COLUMN_ID'])
        assert records[0]['fields']['COLUMN_ID'] == '300'
        assert records[2]['fields']['COLUMN_ID'] == '298'

    def test_get_all_sort_desc_explicit(self, airtable_read):
        records = airtable_read.get_all(maxRecords=5, sort=[('COLUMN_ID', 'asc')])
        assert records[0]['fields']['COLUMN_ID'] == '1'
        assert records[2]['fields']['COLUMN_ID'] == '3'

    def test_get_all_sort_desc_explicit(self, airtable_read):
        records = airtable_read.get_all(maxRecords=5, sort=[('COLUMN_ID', 'desc')])
        assert records[0]['fields']['COLUMN_ID'] == '300'
        assert records[2]['fields']['COLUMN_ID'] == '298'

    def test_get_all_filter(self, airtable_read):
        records = airtable_read.get_all(filterByFormula="COLUMN_ID='5'")
        assert len(records) == 1
        assert records[0]['fields']['COLUMN_ID'] == '5'

    def test_match(self, airtable_read):
        record = airtable_read.match('COLUMN_STR', 'DUPLICATE', view='ViewAll')
        assert isinstance(record, dict)
        assert record['fields'].get('COLUMN_ID') == '2'

    def test_match_not(self, airtable_read):
        record = airtable_read.match('COLUMN_STR', 'FAKE VALUE', view='ViewAll')
        assert isinstance(record, dict)
        assert len(record) == 0

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
        rows = [self.row() for i in range(5)]
        responses = airtable_write.batch_insert(rows)
        for response in responses:
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


class TestAirtableReplace():

    @pytest.fixture
    def old_field(self):
        return {'COLUMN_ID': '1', 'COLUMN_STR': 'UNIQUE', 'COLUMN_UPDATE': 'A'}

    @pytest.fixture
    def new_field(self):
        return {'COLUMN_ID': '1', 'COLUMN_UPDATE': 'B'}

    def test_replace(self, airtable_read, new_field, old_field):
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

        airtable_read.replace(record['id'], new_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'
        assert 'COLUMN_STR' not in record['fields']

        airtable_read.replace(record['id'], old_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'
        assert 'COLUMN_ID' in record['fields']
        assert 'COLUMN_STR' in record['fields']

    def test_replace_by_field(self, airtable_read, new_field, old_field):
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

        airtable_read.replace_by_field('COLUMN_ID', record['fields']['COLUMN_ID'], new_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'
        assert 'COLUMN_STR' not in record['fields']

        airtable_read.replace_by_field('COLUMN_ID', record['fields']['COLUMN_ID'], old_field)
        record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'
        assert 'COLUMN_ID' in record['fields']
        assert 'COLUMN_STR' in record['fields']

class TestAirtableDelete():

    @pytest.fixture
    def row(self):
        return  {'UUID': '4e8f9cfa-543b-492f-962b-e16930b49cae',
                 'String': 'Deleted Test'}

    def test_delete(self, airtable_write, row):
        record = airtable_write.match('UUID', row['UUID'])
        if not record:
            record = airtable_write.insert(row)

        response = airtable_write.delete(record['id'])
        assert response.get('deleted') is True
        assert 'id' in response
        airtable_write.insert(row)

    def test_batch_delete(self, airtable_write, row):
        records = [airtable_write.insert(row)['id'],
                   airtable_write.insert(row)['id']]

        responses = airtable_write.batch_delete(records)
        assert responses[0].get('deleted') is True
        assert responses[1].get('deleted') is True

    def test_batch_delete_by_field(self, airtable_write, row):
        record = airtable_write.match('UUID', row['UUID'])
        if not record:
            record = airtable_write.insert(row)

        response = airtable_write.delete_by_field('UUID', row['UUID'])
        assert response.get('deleted') is True
        airtable_write.insert(row)

class TestAirtableMirror():

    @pytest.fixture
    def row(self):
        return  {'UUID': '4e8f9cfa-543b-492f-962b-e16930b49cae',
                 'String': 'MIRROR'}

    def test_mirror(self, airtable_write, row):
        records = [row, row]
        airtable_write.mirror(records, view='Mirror')
        new_records = airtable_write.get_all(view='Mirror')
        assert len(new_records) == 2

def populate_table_a(self, airtable_write):
    for i in range(4, 300):
        row = {'COLUMN_ID': str(i)}
        resp = airtable_write.insert(row)
        assert resp.ok
