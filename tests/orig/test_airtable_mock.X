from __future__ import absolute_import

import pytest
from requests_mock import Mocker
import requests
import uuid
import posixpath
import os
import json
from six.moves.urllib.parse import urlencode, quote


from airtable import Airtable
from airtable.auth import AirtableAuth

tests_dir = os.path.dirname(__file__)
dumps_dir = os.path.join(tests_dir, 'dump')

def collect_dumps():
    dumps = []
    for dump in os.listdir(dumps_dir):
        dump_filepath = os.path.join(dumps_dir, dump)
        with open(dump_filepath) as fp:
            dump_dict = json.load(fp)
        dumps.append(dump_dict)
    return dumps


@pytest.fixture(scope='session')
def airtable_mock():
    with Mocker() as m:
        url = build_url(TEST_TABLE_NAME, params={'maxRecords': 1})
        m.get(url, status_code=200)
        airtable = Airtable(TEST_BASE_KEY, TEST_TABLE_NAME)
    return airtable


class TestAuth():

    def test_authorization_scheme(self):
        session = requests.Session()
        session.auth = AirtableAuth()
        with Mocker() as m:
            m.get('http://www.google.com', status_code=200)
            resp = session.get('http://www.google.com')
        assert 'Authorization' in resp.request.headers
        assert 'Bearer' in resp.request.headers['Authorization']

    def test_authorization_call(self):
        session = requests.Session()
        auth = AirtableAuth()
        session = auth.__call__(session)
        assert 'Authorization' in session.headers
        assert 'Bearer' in session.headers['Authorization']

    def test_authorization_is(self, airtable_mock):
        assert airtable_mock.is_authenticated


class TestAirtableGet():

    def test_get(self, airtable_mock):
        with Mocker() as m:
            m.get(table_a_url, status_code=200)
            iterator = airtable_read.get(view='ViewAll')
            for n, records in enumerate(iterator, 1):
                assert isinstance(records, list)
                assert len(records) == 100
                assert records[0]['fields']['COLUMN_ID'] in ['1', '101', '201']

    # def test_get_all(self, airtable_read):
    #     records = airtable_read.get_all()
    #     assert isinstance(records, list)
    #     assert len(records) == 300
    #
    # def test_get_pagesize(self, airtable_read):
    #     for records in airtable_read.get(pageSize=60):
    #         assert len(records) == 60
    #         break
    #
    # def test_get_all_view(self, airtable_read):
    #     records = airtable_read.get_all(view='ViewOne')
    #     assert len(records) == 1
    #
    # def test_get_all_maxrecords(self, airtable_read):
    #     records = airtable_read.get_all(maxRecords=50)
    #     assert len(records) == 50
    #
    # def test_match(self, airtable_read):
    #     record = airtable_read.match('COLUMN_STR', 'DUPLICATE', view='ViewAll')
    #     assert isinstance(record, dict)
    #     assert record['fields'].get('COLUMN_ID') == '2'
    #
    # def test_search(self, airtable_read):
    #     records = airtable_read.search('COLUMN_STR', 'DUPLICATE', view='ViewAll')
    #     assert isinstance(records, list)
    #     assert len(records) == 2
    #     assert records[0]['fields'].get('COLUMN_ID') == '2'
    #     assert records[1]['fields'].get('COLUMN_ID') == '3'
    #     assert all([True for r in records if r['fields']['COLUMN_STR'] == 'DUPLICATE'])
#
#
# class TestAirtableCreate():
#
#     @pytest.fixture
#     def row(self):
#         return  {'UUID': str(uuid.uuid4()), 'String': 'TestAirTableCreate'}
#
#     def test_create_one(self, row, airtable_write):
#         response = airtable_write.insert(row)
#         assert 'id' in response
#
#     def test_create_batch(self, airtable_write):
#         rows = [self.row() for i in range(5)]
#         responses = airtable_write.batch_insert(rows)
#         for response in responses:
#             assert 'id' in response
#
#
# class TestAirtableUpdate():
#
#     @pytest.fixture
#     def old_field(self):
#         return {'COLUMN_UPDATE': 'A'}
#
#     @pytest.fixture
#     def new_field(self):
#         return {'COLUMN_UPDATE': 'B'}
#
#     def test_update(self, airtable_read, new_field, old_field):
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'A'
#
#         airtable_read.update(record['id'], new_field)
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'B'
#
#         airtable_read.update(record['id'], old_field)
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'A'
#
#     def test_update_by_field(self, airtable_read, new_field, old_field):
#         airtable_read.update_by_field('COLUMN_UPDATE', 'A', new_field)
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'B'
#
#         airtable_read.update(record['id'], old_field)
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'A'
#
#
# class TestAirtableReplace():
#
#     @pytest.fixture
#     def old_field(self):
#         return {'COLUMN_ID': '1', 'COLUMN_STR': 'UNIQUE', 'COLUMN_UPDATE': 'A'}
#
#     @pytest.fixture
#     def new_field(self):
#         return {'COLUMN_UPDATE': 'B'}
#
#     def test_replace(self, airtable_read, new_field, old_field):
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'A'
#
#         airtable_read.replace(record['id'], new_field)
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'B'
#         assert 'COLUMN_ID' not in record['fields']
#         assert 'COLUMN_STR' not in record['fields']
#
#         airtable_read.replace(record['id'], old_field)
#         record = airtable_read.get_all(maxRecords=1, view='ViewAll')[0]
#         assert record['fields']['COLUMN_UPDATE'] == 'A'
#         assert 'COLUMN_ID' in record['fields']
#         assert 'COLUMN_STR' in record['fields']
#
#
# class TestAirtableDelete():
#
#     @pytest.fixture
#     def row(self):
#         return  {'UUID': '4e8f9cfa-543b-492f-962b-e16930b49cae',
#                  'String': 'Deleted Test'}
#
#     def test_delete(self, airtable_write, row):
#         record = airtable_write.match('UUID', row['UUID'])
#         if not record:
#             record = airtable_write.insert(row)
#
#         response = airtable_write.delete(record['id'])
#         assert response.get('deleted') is True
#         assert 'id' in response
#         airtable_write.insert(row)
#
#     def test_batch_delete(self, airtable_write, row):
#         records = [airtable_write.insert(row)['id'],
#                    airtable_write.insert(row)['id']]
#
#         responses = airtable_write.batch_delete(records)
#         assert responses[0].get('deleted') is True
#         assert responses[1].get('deleted') is True
#
#
# class TestAirtableMirror():
#
#     @pytest.fixture
#     def row(self):
#         return  {'UUID': '4e8f9cfa-543b-492f-962b-e16930b49cae',
#                  'String': 'MIRROR'}
#
#     def test_mirror(self, airtable_write, row):
#         records = [row, row]
#         airtable_write.mirror(records, view='Mirror')
#         assert len(airtable_write.get_all(view='Mirror')) == 2
