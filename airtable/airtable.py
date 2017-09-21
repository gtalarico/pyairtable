"""
Airtable Python Wrapper

>>> airtable = Airtable('base_key', 'table_name')
>>> airtable.get_all()
[{{'fields': {{...}}, ...}}]

"""  #

__author__ = 'Gui Talarico'
__version__ = '0.7.0'
__release__ = 'dev1'

import os
import json
import requests
import posixpath
import time
from six.moves.urllib.parse import urlencode

from .auth import AirtableAuth
from .params import AirtableParams


class Airtable():

    VERSION = 'v0'
    API_BASE_URL = 'https://api.airtable.com/'
    API_LIMIT = 1.0 / 5  # 5 per second
    API_URL = posixpath.join(API_BASE_URL, VERSION)

    def __init__(self, base_key, table_name, api_key=None):
        """
        If api_key is not provided, :any:`AirtableAuth` will attempt
        to use ``os.environ['AIRTABLE_API_KEY']``
        """
        session = requests.Session()
        session.auth = AirtableAuth(api_key=api_key)
        self.session = session
        self.url_table = posixpath.join(self.API_URL, base_key, table_name)
        self.is_authenticated = self.validate_session(self.url_table)

    def validate_session(self, url):
        response = self.session.get(url, params={'maxRecords': 1})
        if response.ok:
            return True
        elif response.status_code == 404:
            raise ValueError('Invalid base or table name: {}'.format(url))
        else:
            raise ValueError('Authentication failed: {}'.format(response.reason))

    def _process_params(self, params):
        """
        Process params names or values as needed using filters
        """
        for param_name, param_value in params.copy().items():
            param_value = params.pop(param_name)
            ParamClass = AirtableParams.get(param_name)
            new_param = ParamClass(param_value).to_param_dict()
            params.update(new_param)
        return params

    def _process_response(self, response):
        response.raise_for_status()
        return response.json()

    def record_url(self, record_id):
        """ Builds URL with record id """
        return posixpath.join(self.url_table, record_id)

    def _request(self, method, url, params=None, json_data=None):
        response = self.session.request(method, url, params=params, json=json_data)
        return self._process_response(response)

    def _get(self, url, **params):
        processed_params = self._process_params(params)
        return self._request('get', url, params=processed_params)

    def _post(self, url, json_data):
        return self._request('post', url, json_data=json_data)

    def _put(self, url, json_data):
        return self._request('put', url, json_data=json_data)

    def _patch(self, url, json_data):
        return self._request('patch', url, json_data=json_data)

    def _delete(self, url):
        return self._request('delete', url)

    def get(self, record_id):
        """
        Retrieves a record by its id

        >>> record = airtable.get('recwPQIfs4wKPyc9D')

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Record
        """
        record_url = self.record_url(record_id)
        return self._get(record_url)

    def get_iter(self, **options):
        """
        Record Retriever Iterator

        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :any:`get_all`

        >>> for records in airtable.get_iter():
        >>>     print(records)
        [{'fields': ... }, ...]

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): The name or ID of a view.
                If set, only the records in that view will be returned.
                The records will be sorted according to the order of the view.
            pageSize (``int``): The number of records returned in each request.
                Must be less than or equal to 100. Default is 100.
            fields (``str``, ``list``): Name of field or fields to be retrieved.
                Default is all fields
            sort (``list``): List of fields to sort by. Default order is
                ascending. To control direction, use prefix '-' for descending,
                or pass tuples [('field', 'asc'), ('field', 'desc')]
            formula (``str``): Airtable formula.

        Returns:
            iterator (``list``): List of Records, grouped by pageSize

        """
        offset = None
        while True:
            data = self._get(self.url_table, offset=offset, **options)
            records = data.get('records', [])
            yield records
            offset = data.get('offset')
            if not offset:
                break

    def get_all(self, **options):
        """
        Retrieves all records repetitively and returns a single list.

        >>> airtable.get_all()
        >>> airtable.get_all(view='MyView')
        >>> airtable.get_all(maxRecords=50)
        [{'fields': ... }, ...]

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): The name or ID of a view.
                If set, only the records in that view will be returned.
                The records will be sorted according to the order of the view.
            fields (``str``, ``list``): Name of field or fields to be retrieved.
                Default is all fields
            sort (``list``): List of fields to sort by. Default order is
                ascending. To control direction, use prefix '-' for descending,
                or pass tuples [('field', 'asc'), ('field', 'desc')]
            formula (``str``): Airtable formula.

        Returns:
            records (``list``): List of Records

        >>> records = get_all(maxRecords=3, view='All')

        """
        all_records = []
        for records in self.get_iter(**options):
            all_records.extend(records)
        return all_records

    def match(self, field_name, field_value, **options):
        """
        Returns first match found in :any:`get_all`

        >>> airtable.match('Name', 'John')
        {'fields': {'Name': 'John'} }

        Args:
            field_name (``str``): Name of field to match (column name)
            field_value (``str``): Value of field to match

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): The name or ID of a view.
                If set, only the records in that view will be returned.
                The records will be sorted according to the order of the view.
            fields (``str``, ``list``): Name of field or fields to be retrieved.
                Default is all fields
            sort (``list``): List of fields to sort by. Default order is
                ascending. To control direction, use prefix '-' for descending,
                or pass tuples [('field', 'asc'), ('field', 'desc')]
            formula (``str``): Airtable formula.

        Returns:
            record (``dict``): First record to match the field_value provided
        """
        for record in self.get_all(**options):
            if record.get('fields', {}).get(field_name) == field_value:
                return record
        else:
             return {}

    def search(self, field_name, field_value, record=None, **options):
        """
        Returns All matching records found in :any:`get_all`


        >>> airtable.search('Gender', 'Male')
        [{'fields': {'Name': 'John', 'Gender': 'Male'}, ... ]

        Args:
            field_name (``str``)
            field_value (``str``)

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): The name or ID of a view.
                If set, only the records in that view will be returned.
                The records will be sorted according to the order of the view.
            fields (``str``, ``list``): Name of field or fields to be retrieved.
                Default is all fields
            sort (``list``): List of fields to sort by. Default order is
                ascending. To control direction, use prefix '-' for descending,
                or pass tuples [('field', 'asc'), ('field', 'desc')]
            formula (``str``): Airtable formula.

        Returns:
            records (``list``): All records that matched ``field_value``
        """
        records = []
        for record in self.get_all(**options):
            if record.get('fields', {}).get(field_name) == field_value:
                records.append(record)
        return records

    def insert(self, fields):
        """
        Inserts a record

        >>> record = {'Name': 'John'}
        >>> airtable.insert(record)

        Args:
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.

        Returns:
            record (``dict``): Inserted record
        """
        return self._post(self.url_table, json_data={"fields": fields})

    def _batch_request(self, func, iterable):
        """ Internal Function to limit batch calls to API limit """
        responses = []
        for item in iterable:
            responses.append(func(item))
            time.sleep(self.API_LIMIT)
        return responses

    def batch_insert(self, records):
        """
        Calls :any:`insert` repetitively, following set API Rate Limit (5/sec)
        To change the rate limit use ``airtable.API_LIMIT = 0.2`` (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert(records)

        Args:
            records(``list``): Records to insert

        Returns:
            records (``list``): list of added records

        """
        return self._batch_request(self.insert, records)

    def update(self, record_id, fields):
        """
        Updates a record by its record id or by matching fields.

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> fields = {'Status': 'Fired'}
        >>> airtable.update(record['id'], fields)

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key

        Returns:
            record (``dict``): Updated record
        """
        record_url = self.record_url(record_id)
        return self._patch(record_url, json_data={"fields": fields})

    def update_by_field(self, field_name, field_value, fields, **options):
        """
        Updates a record with first match.

        >>> record = {'Name': 'John', 'Tel': '540-255-5522'}
        >>> airtable.update_by_field('Name', 'John', record)

        Args:
            field_name(``str``): Name of the field to search
            field_value(``str``): Value to match
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve

        Returns:
            record (``dict``): Updated record
        """
        record = self.match(field_name, field_value, **options)
        return {} if not record else self.update(record['id'], fields)

    def replace(self, record_id, fields):
        """
        Replaces a record by its record id

        >>> record = airtable.match('Seat Number', '22A')
        >>> fields = {'PassangerName': 'Mike', 'Passport': 'YASD232-23'}
        >>> airtable.replace(record['id'], fields)

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to replace. Must be dictionary with Column names as Key

        Returns:
            record (``dict``): New record
        """
        record_url = self.record_url(record_id)
        return self._put(record_url, json_data={"fields": fields})

    def replace_by_field(self, field_name, field_value, fields, **options):
        """
        Replaces a record with first match.

        Args:
            field_name(``str``): Name of the field to search
            field_value(``str``): Value to match
            fields(``dict``): Fields to replace with.
                Must be dictionary with Column names as Key

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to replace. Must be dictionary with Column names as Key

        Returns:
            record (``dict``): New record
        """
        record = self.match(field_name, field_value, **options)
        return {} if not record else self.replace(record['id'], fields)

    def delete(self, record_id):
        """
        Deletes a record by its id

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> airtable.delete(record['id'])

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Deleted Record
        """
        record_url = self.record_url(record_id)
        return self._delete(record_url)

    def delete_by_field(self, field_name, field_value, **options):
        """
        Deletes first record  to match provided field and value

        >>> record = airtable.delete_by_field('Employee Id', 'DD13332454')

        Args:
            field_name(``str``): Name of the field to search
            field_value(``str``): Value to match

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve

        Returns:
            record (``dict``): Deleted Record
        """

        record = self.match(field_name, field_value, **options)
        record_url = self.record_url(record['id'])
        return self._delete(record_url)


    def batch_delete(self, record_ids):
        """
        Calls :any:`delete` repetitively, following set API Rate Limit (5/sec)
        To change the rate limit use ``airtable.API_LIMIT = 0.2`` (5 per second)

        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> airtable.batch_delete(records)

        Args:
            records(``list``): Record Ids to delete

        Returns:
            records (``list``): list of records deleted

        """
        return self._batch_request(self.delete, record_ids)


    def mirror(self, records, **options):
        """
        Deletes all records on table or view and replaces with records.

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]

        >>> record = airtable.,mirror(records)

        If view options are provided, only records visible on that view will
        be deleted.

        >>> record = airtable.mirror(records, view='View')
        ([{'id': 'recwPQIfs4wKPyc9D', ... }], [{'deleted': True, ... }])

        Args:
            records(``list``): Records to insert

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve

        Returns:
            records (``tuple``): (new_records, deleted_records)
        """

        all_record_ids = [r['id'] for r in self.get_all(**options)]
        deleted_records = self.batch_delete(all_record_ids)
        new_records = self.batch_insert(records)
        return (new_records, deleted_records)
