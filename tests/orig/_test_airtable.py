from __future__ import absolute_import

import pytest
import os
import requests
from requests_mock import Mocker
from posixpath import join as urljoin
from requests.exceptions import HTTPError

from airtable.params import AirtableParams

from .pytest_fixtures import mock_airtable, airtable, Airtable, build_url
from .pytest_fixtures import table_url, base_key, table_name, fake_api_key
from .pytest_fixtures import table_data, reset_table, clean_airtable


class TestInit():

    def test_repr(self, mock_airtable):
        assert '<Airtable' in mock_airtable.__repr__()
        assert table_name in mock_airtable.__repr__()

    def test_is_authenticated(self, mock_airtable):
        assert mock_airtable.is_authenticated


class TestMethods():

    def test_record_url(self, mock_airtable):
        record_id = 'rec123456'
        record_url = urljoin(table_url, record_id)
        assert record_url == mock_airtable.record_url(record_id)

    def test_validate_session(self, mock_airtable):
        with Mocker() as m:
            mock_url = build_url(base_key, table_name, params={'maxRecords': 1})
            m.get(mock_url, status_code=200)
            airtable = Airtable(base_key, table_name, api_key=fake_api_key)


@pytest.mark.usefixtures("clean_airtable")
class TestGet():

    def test_get(self, airtable):
        record = airtable.get('rec0LQoJ4Vgp8fPty')
        assert isinstance(record, dict)
        assert record['id'] == 'rec0LQoJ4Vgp8fPty'

    def test_get_iter(self, airtable):
        for n, records in enumerate(airtable.get_iter(), 1):
            assert isinstance(records, list)
            assert len(records) == 100 or 4

    def test_get_all(self, airtable):
        records = airtable.get_all()
        assert isinstance(records, list)
        assert len(records) == 104

    def test_get_all(self, airtable):
        records = airtable.get_all(max_records=3)
        assert isinstance(records, list)
        assert len(records) == 3

    def test_get_pagesize(self, airtable):
        for records in airtable.get_iter(pageSize=50):
            assert len(records) == 50
            break

    def test_get_all_view(self, airtable):
        records = airtable.get_all(view='One')
        assert len(records) == 1

    def test_get_bad_param(self, airtable):
        with pytest.raises(ValueError) as excinfo:
            airtable.get_all(view='One', bad_param=True)
            assert 'invalid param keyword' in str(excinfo.value).lower()

    def test_get_bad_request_decoded_msg(self, airtable):
        with pytest.raises(HTTPError) as excinfo:
            airtable.get_all(view='One', sort=['NON_EXISTING'], fields=['X'])
            assert 'Unprocessable Entity for url(decoded)' in str(excinfo.value).lower()
            assert 'sort[0]' in str(excinfo.value).lower()
            assert 'fields[]=' in str(excinfo.value).lower()

    def test_get_all_fields_single(self, airtable):
        records = airtable.get_all(view='ViewAll', maxRecords=1,
                                   fields=['COLUMN_STR'])
        assert 'COLUMN_STR' in records[0]['fields']
        assert 'COLUMN_INT' not in records[0]['fields']

    def test_get_all_fields_multiple(self, airtable):
        records = airtable.get_all(view='ViewAll', maxRecords=1,
                                   fields=['COLUMN_INT', 'COLUMN_STR'])
        assert 'COLUMN_STR' in records[0]['fields']
        assert 'COLUMN_INT' in records[0]['fields']

    def test_get_all_maxrecords(self, airtable):
        records = airtable.get_all(maxRecords=50)
        assert len(records) == 50

    def test_get_all_max_records(self, airtable):
        records = airtable.get_all(max_records=50)
        assert len(records) == 50

    def test_get_all_sort_asc(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=['COLUMN_INT'])
        assert records[0]['fields']['COLUMN_INT'] == 1
        assert records[2]['fields']['COLUMN_INT'] == 3

    def test_get_all_sort_asc_str(self, airtable):
        records = airtable.get_all(maxRecords=5, sort='COLUMN_INT')
        assert records[0]['fields']['COLUMN_INT'] == 1
        assert records[2]['fields']['COLUMN_INT'] == 3

    def test_get_all_sort_desc(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=['-COLUMN_INT'])
        assert records[0]['fields']['COLUMN_INT'] == 104
        assert records[1]['fields']['COLUMN_INT'] == 104
        assert records[2]['fields']['COLUMN_INT'] == 103

    def test_get_all_sort_desc_explicit(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=[('COLUMN_INT', 'asc')])
        assert records[0]['fields']['COLUMN_INT'] == 1
        assert records[2]['fields']['COLUMN_INT'] == 3

    def test_get_all_sort_desc_explicit(self, airtable):
        records = airtable.get_all(maxRecords=5, sort=[('COLUMN_INT', 'desc')])
        assert records[0]['fields']['COLUMN_INT'] == 104
        assert records[1]['fields']['COLUMN_INT'] == 104
        assert records[2]['fields']['COLUMN_INT'] == 103

    def test_get_all_filter(self, airtable):
        records = airtable.get_all(filterByFormula="COLUMN_INT=5")
        assert len(records) == 1
        assert records[0]['fields']['COLUMN_INT'] == 5

    def test_match(self, airtable):
        record = airtable.match('COLUMN_INT', 5, view='ViewAll')
        assert isinstance(record, dict)
        assert record['fields'].get('COLUMN_INT') == 5

    def test_match_not(self, airtable):
        record = airtable.match('COLUMN_STR', 'FAKE VALUE', view='ViewAll')
        assert isinstance(record, dict)
        assert len(record) == 0

    def test_search(self, airtable):
        records = airtable.search('COLUMN_INT', 104, view='ViewAll')
        assert isinstance(records, list)
        assert len(records) == 2
        assert records[0]['fields'].get('COLUMN_INT') == 104
        assert records[1]['fields'].get('COLUMN_INT') == 104

    def test_search_not(self, airtable):
        records = airtable.search('COLUMN_INT', 999, view='ViewAll')
        assert isinstance(records, list)
        assert len(records) == 0

    def test_formula_from_name_and_value(self, airtable):
        formula = AirtableParams.FormulaParam.from_name_and_value('COL', 'VAL')
        assert formula == "{COL}='VAL'"

        formula = AirtableParams.FormulaParam.from_name_and_value('COL', 8)
        assert formula == "{COL}=8"


@pytest.mark.usefixtures("clean_airtable")
class TestCreate():

    def test_create_one(self, airtable):
        record = {'COLUMN_INT': 999}
        response = airtable.insert(record)
        assert 'id' in response
        assert response['fields']['COLUMN_INT'] == 999

    def test_create_one_typecast(self, airtable):
        record = {'COLUMN_INT': '50'}
        response = airtable.insert(record, typecast=True)
        assert 'id' in response
        assert response['fields']['COLUMN_INT'] == 50

    def test_create_batch(self, airtable):
        rows = [{'COLUMN_INT': i} for i in range(200, 203)]
        responses = airtable.batch_insert(rows)
        assert len(responses) == 3
        for response in responses:
            assert 'id' in response
            assert response['fields']['COLUMN_INT'] in range(200, 203)

    def test_create_type_mismatch(self, airtable):
        """ Verify Exception and Exception Message on Type Mismatch """
        record = {'COLUMN_INT': 'aaa'}
        with pytest.raises(requests.exceptions.HTTPError) as exc:
            response = airtable.insert(record)
        assert 'INVALID_VALUE_FOR_COLUMN' in str(exc)
        assert 'Field COLUMN_INT can not accept value aaa' in str(exc)


@pytest.mark.usefixtures("clean_airtable")
class TestUpdate():

    @pytest.fixture
    def old_field(self):
        return {'COLUMN_INT': 1}

    @pytest.fixture
    def new_field(self):
        return {'COLUMN_INT': 500}

    def test_update(self, airtable, new_field, old_field):
        record = airtable.match('COLUMN_INT', 104)
        assert record['fields']['COLUMN_INT'] == 104

        new_record = airtable.update(record['id'], new_field)
        record = airtable.get(new_record['id'])
        assert record['fields']['COLUMN_INT'] == 500
        assert 'COLUMN_STR' in record['fields']

    def test_update_by_field(self, airtable, new_field, old_field):
        new_record = airtable.update_by_field('COLUMN_INT', 104,
                                              new_field, sort='COLUMN_INT')
        record = airtable.get(new_record['id'])
        assert record['fields']['COLUMN_INT'] == 500

@pytest.mark.usefixtures("clean_airtable")
class TestReplace():

    @pytest.fixture
    def old_field(self):
        return {'COLUMN_INT': 1}

    @pytest.fixture
    def new_field(self):
        return {'COLUMN_INT': 500}

    def test_replace(self, airtable, new_field, old_field):
        record = airtable.match('COLUMN_INT', 104)
        assert record['fields']['COLUMN_INT'] == 104

        new_record = airtable.replace(record['id'], new_field)
        record = airtable.get(new_record['id'])
        assert record['fields']['COLUMN_INT'] == 500
        assert 'COLUMN_STR' not in record['fields']

    def test_replace_by_field(self, airtable, new_field, old_field):
        new_record = airtable.replace_by_field('COLUMN_INT', 103,
                                              new_field, sort='COLUMN_INT')
        record = airtable.get(new_record['id'])
        assert record['fields']['COLUMN_INT'] == 500
        assert 'COLUMN_STR' not in record['fields']


@pytest.mark.usefixtures("clean_airtable")
class TestDelete():

    def test_delete(self, airtable):
        record = airtable.match('COLUMN_INT', 100)
        assert record['fields']['COLUMN_INT'] == 100

        record = airtable.delete(record['id'])
        assert record.get('deleted') is True
        assert 'id' in record

        assert len(airtable.match('COLUMN_INT', 100)) == 0


    def test_batch_delete(self, airtable):
        record = airtable.match('COLUMN_INT', 104)
        assert record['fields']['COLUMN_INT'] == 104
        record2 = airtable.match('COLUMN_INT', 103)
        assert record2['fields']['COLUMN_INT'] == 103

        records = airtable.batch_delete([record['id'], record2['id']])
        assert records[0].get('deleted') is True
        assert records[1].get('deleted') is True

    def test_delete_by_field(self, airtable):
        record = airtable.match('COLUMN_INT', 102)
        assert record['fields']['COLUMN_INT'] == 102

        record = airtable.delete_by_field('COLUMN_INT', 102)
        assert record.get('deleted') is True

@pytest.mark.usefixtures("clean_airtable")
class TestAirtableMirror():

    def test_mirror(self, airtable):
        records = [{'COLUMN_INT': 100}, {'COLUMN_INT': 100}, {'COLUMN_INT': 100}]
        airtable.mirror(records, view='One')
        new_records = airtable.get_all(view='One')
        assert len(new_records) == 3
