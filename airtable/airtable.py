"""
Airtable Python Wrapper

>>> airtable = Airtable('base_key', 'table_name')
>>> airtable.get_all()
[{{'fields': {{...}}, ...}}]

"""  #

__author__ = 'Gui Talarico'
__version__ = '0.3.0'

import os
import json
import requests
import posixpath
import time
from six.moves.urllib.parse import urlencode

from .auth import AirtableAuth


class Airtable():

    _VERSION = 'v0'
    _API_BASE_URL = 'https://api.airtable.com/'

    API_URL = posixpath.join(_API_BASE_URL, _VERSION)
    ALLOWED_PARAMS = 'view maxRecords offset pageSize'.split()  # Not implemented: 'fields sort filterByFormula'
    API_LIMIT = 1.0 / 5  # 5 per second

    def __init__(self, base_key, table_name, api_key=None):
        """
        If api_key is not provided, AirtableAuth will attempt
        to use os.environ['AIRTABLE_API_KEY']
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

    def _process_response(self, response):
        response.raise_for_status()  # Raises if Status Code is not 200's
        return response.json()

    def record_url(self, record_id):
        return posixpath.join(self.url_table, record_id)

    def _get(self, url, **params):
        if any([True for option in params.keys() if option not in self.ALLOWED_PARAMS]):
            raise ValueError('invalid url param: {}'.format(params.keys()))
        return self._process_response(self.session.get(url, params=params))

    def _post(self, url, json_data):
        return self._process_response(self.session.post(url, json=json_data))

    def _patch(self, url, json_data):
        return self._process_response(self.session.patch(url, json=json_data))

    def _delete(self, url):
        return self._process_response(self.session.delete(url))

    def get(self, **options):
        """
        Record Retriever Iterator

        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :any:`get_all`

        >>> for records in airtable.get():
        >>>     print(records)
        [{'fields': ... }, ...]

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): The name or ID of a view.
                If set, only the records in that view will be returned.
                The records will be sorted according to the order of the view.
            pageSize (``int``): The number of records returned in each request.
                Must be less than or equal to 100. Default is 100.

            sort (``list``): Not Implemented
            filterByFormula (``str``): Not Implemented
            fields (``list``): Not Implemented

        Returns:
            iterator (``list``): List of Records, grouped by pageSize

        """
        offset = None
        while True:
            response_data = self._get(self.url_table, offset=offset, **options)
            records = response_data.get('records', [])
            yield records
            offset = response_data.get('offset')
            if not offset:
                break

    def get_all(self, **options):
        """
        Retrieves all records iteratibely and returns a single list.

        >>> airtable.get_all()
        >>> airtable.get_all(view='MyView')
        >>> airtable.get_all(maxRecords=50)
        [{'fields': ... }, ...]

        Keyword Args:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve

        Returns:
            records (``list``): List of Records

        >>> records = get_all(maxRecords=3, view='All')

        """
        all_records = []
        for records in self.get(**options):
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
            maxRecords (``int``): Maximum number of records to retrieve

        Returns:
            record (``dict``): First record to match the field_value provided
        """
        for record in self.get_all(**options):
            if record.get('fields', {}).get(field_name) == field_value:
                return record

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
            maxRecords (``int``): Maximum number of records to retrieve

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
            fields(``dict``): Fields to add. Must be dictionary with Column names as Key.
                Does not need to include key ``fields``

        Returns:
            record (``dict``): Inserted record
        """
        return self._post(self.url_table, json_data={"fields": fields})

    def _batch_request(self, iterable, func):
        responses = []
        for item in iterable:
            responses.append(func(item))
            time.sleept(self.API_LIMIT)
        return responses

    def batch_insert(self, rows):
        """
        Calls :any:`insert` iteratibely, following set API Rate Limit (5/sec)
        To change the rate limit use ``airtable.API_LIMIT = 0.2` (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert(records)

        Args:
            rows(``list``): Records to insert

        Returns:
            records (``list``): list of added records

        """
        self._batch_request(rows, self.insert)

    def update(self, record_id, fields):
        """
        Updates a record

        >>> record = {'Name': 'John'}
        >>> airtable.update(record)

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to add. Must be dictionary with Column names as Key

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
            fields(``dict``): Fields to add. Must be dictionary with Column names as Key

        Returns:
            record (``dict``): Updated record
        """
        record = self.match(field_name, field_value, **options)
        if record:
            record_url = self.record_url(record['id'])
            return self._patch(record_url, json_data={"fields": fields})

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

        Returns:
            record (``dict``): Deleted Record
        """
        recor
        record = self.match(field_name, field_value, **options)
        record_url = self.record_url(record['id'])
        return self._delete(record_url)
