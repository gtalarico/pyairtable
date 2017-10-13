from __future__ import absolute_import

import pytest
import os
import requests
import uuid
from collections import defaultdict
from requests.exceptions import HTTPError

from pytest_fixtures import airtable


TEST_BASE_KEY = 'appJMY16gZDQrMWpA'
TEST_TABLE_A = 'TABLE READ'
TEST_TABLE_B = 'TABLE WRITE'

filepath = os.path.join('tests', 'mock_responses.json')

responses = {'GET': defaultdict(list),
             'POST': defaultdict(list),
             'DELETE': defaultdict(list),
             'PATCH': defaultdict(list)
             }

def _dump_request_data(process_response_func):
    def wrapper(response):
        url = response.request.url
        method = response.request.method
        status = response.status_code
        try:
            response_json = response.json()
        except:
            response_json = None

        responses[method] = {'url': url,
                             'status': status,
                             ' response_json': response_json}
        return process_response_func(response)
    return wrapper



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

"""




class TestAirtableGet():

    def test_repr(self, airtable):
        assert '<Airtable' in airtable.__repr__()
        assert airtable.table_name in airtable.__repr__()

    def test_get(self, airtable):
        record = airtable.get('recwPQIfs4wKPyc9D')
        assert isinstance(record, dict)
        assert record['id'] == 'recwPQIfs4wKPyc9D'

    def test_get_iter(self, airtable):
        for n, records in enumerate(airtable.get_iter(view='ViewAll'), 1):
            assert isinstance(records, list)
            assert len(records) == 100
            assert records[0]['fields']['COLUMN_ID'] in ['1', '101', '201']

    def test_get_all(self, airtable):
        records = airtable.get_all()
        assert isinstance(records, list)
        assert len(records) == 300

    def test_get_pagesize(self, airtable):
        for records in airtable.get_iter(pageSize=60):
            assert len(records) == 60
            break

    def test_get_all_view(self, airtable):
        records = airtable.get_all(view='ViewOne')
        assert len(records) == 1

    def test_get_bad_param(self, airtable):
        with pytest.raises(ValueError) as excinfo:
            airtable.get_all(view='ViewOne', bad_param=True)
            assert 'invalid param keyword' in str(excinfo.value).lower()

    def test_get_bad_request_decoded_msg(self, airtable):
        with pytest.raises(HTTPError) as excinfo:
            airtable.get_all(view='ViewOne', sort=['NON_EXISTING'], fields=['X'])
            assert 'Unprocessable Entity for url(decoded)' in str(excinfo.value).lower()
            assert 'sort[0]' in str(excinfo.value).lower()
            assert 'fields[]=' in str(excinfo.value).lower()

    def test_get_all_fields_single(self, airtable):
        records = airtable.get_all(view='ViewAll', maxRecords=1,
                                        fields=['COLUMN_UPDATE'])
        assert 'COLUMN_ID' not in records[0]['fields']
        assert 'COLUMN_STR' not in records[0]['fields']
        assert 'COLUMN_UPDATE' in records[0]['fields']

    def test_get_all_fields_multiple(self, airtable):
        records = airtable.get_all(view='ViewAll', maxRecords=1,
                                        fields=['COLUMN_UPDATE', 'COLUMN_ID'])
        assert 'COLUMN_ID' in records[0]['fields']
        assert 'COLUMN_UPDATE' in records[0]['fields']
        assert 'COLUMN_STR' not in records[0]['fields']

    def test_get_all_maxrecords(self, airtable):
        records = airtable.get_all(maxRecords=50)
        assert len(records) == 50

    def test_get_all_sort_asc(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=['COLUMN_ID'])
        assert records[0]['fields']['COLUMN_ID'] == '1'
        assert records[2]['fields']['COLUMN_ID'] == '3'

    def test_get_all_sort_asc_str(self, airtable):
        records = airtable.get_all(maxRecords=5, sort='COLUMN_ID')
        assert records[0]['fields']['COLUMN_ID'] == '1'
        assert records[2]['fields']['COLUMN_ID'] == '3'

    def test_get_all_sort_desc(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=['-COLUMN_ID'])
        assert records[0]['fields']['COLUMN_ID'] == '300'
        assert records[2]['fields']['COLUMN_ID'] == '298'

    def test_get_all_sort_desc_explicit(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=[('COLUMN_ID', 'asc')])
        assert records[0]['fields']['COLUMN_ID'] == '1'
        assert records[2]['fields']['COLUMN_ID'] == '3'

    def test_get_all_sort_desc_explicit(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=[('COLUMN_ID', 'desc')])
        assert records[0]['fields']['COLUMN_ID'] == '300'
        assert records[2]['fields']['COLUMN_ID'] == '298'

    def test_get_all_filter(self, airtable):
        records = airtable.get_all(filterByFormula="COLUMN_ID='5'")
        assert len(records) == 1
        assert records[0]['fields']['COLUMN_ID'] == '5'

    def test_match(self, airtable):
        record = airtable.match('COLUMN_STR', 'DUPLICATE', view='ViewAll')
        assert isinstance(record, dict)
        assert record['fields'].get('COLUMN_ID') == '2'

    def test_match_not(self, airtable):
        record = airtable.match('COLUMN_STR', 'FAKE VALUE', view='ViewAll')
        assert isinstance(record, dict)
        assert len(record) == 0

    def test_search(self, airtable):
        records = airtable.search('COLUMN_STR', 'DUPLICATE', view='ViewAll')
        assert isinstance(records, list)
        assert len(records) == 2
        assert records[0]['fields'].get('COLUMN_ID') == '2'
        assert records[1]['fields'].get('COLUMN_ID') == '3'
        assert all([True for r in records if r['fields']['COLUMN_STR'] == 'DUPLICATE'])

    def test_formula_from_name_and_value(self, airtable):
        formula = airtable.formula_from_name_and_value('COL', 'VAL')
        assert formula == "{COL}='VAL'"

        formula = airtable.formula_from_name_and_value('COL', 8)
        assert formula == "{COL}=8"


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

    def test_update(self, airtable, new_field, old_field):
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

        airtable.update(record['id'], new_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'

        airtable.update(record['id'], old_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

    def test_update_by_field(self, airtable, new_field, old_field):
        airtable.update_by_field('COLUMN_UPDATE', 'A', new_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'

        airtable.update(record['id'], old_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'


class TestAirtableReplace():

    @pytest.fixture
    def old_field(self):
        return {'COLUMN_ID': '1', 'COLUMN_STR': 'UNIQUE', 'COLUMN_UPDATE': 'A'}

    @pytest.fixture
    def new_field(self):
        return {'COLUMN_ID': '1', 'COLUMN_UPDATE': 'B'}

    def test_replace(self, airtable, new_field, old_field):
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

        airtable.replace(record['id'], new_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'
        assert 'COLUMN_STR' not in record['fields']

        airtable.replace(record['id'], old_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'
        assert 'COLUMN_ID' in record['fields']
        assert 'COLUMN_STR' in record['fields']

    def test_replace_by_field(self, airtable, new_field, old_field):
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'A'

        airtable.replace_by_field('COLUMN_ID', record['fields']['COLUMN_ID'], new_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
        assert record['fields']['COLUMN_UPDATE'] == 'B'
        assert 'COLUMN_STR' not in record['fields']

        airtable.replace_by_field('COLUMN_ID', record['fields']['COLUMN_ID'], old_field)
        record = airtable.get_all(maxRecords=1, view='ViewAll')[0]
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



class TestAirtableMethods():

    def test_record_url(self, mock_airtable):
        record_id = 'rec123456'
        record_url = posixpath.join(table_url, record_id)
        assert record_url == mock_airtable.record_url(record_id)

    def test_is_repr(self, mock_airtable):
        assert '<Airtable table' in mock_airtable.__repr__()
        assert table_name in mock_airtable.__repr__()
