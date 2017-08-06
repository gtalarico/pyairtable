""" Airtable Python Wrapper  """

__author__ = 'Gui Talarico'
__version__ = '0.2.0.dev1'

import os
import json
import requests
import posixpath
import time
from six.moves.urllib.parse import urlencode

from ._auth import AirtableAuth


class Airtable():

    _VERSION = 'v0'
    _API_BASE_URL = 'https://api.airtable.com/'

    API_URL = posixpath.join(_API_BASE_URL, _VERSION)
    ALLOWED_PARAMS = ['view', 'maxRecords', 'offset', 'sort']
    API_LIMIT = 1.0 / 5  # 5 per second

    def __init__(self, base_key, table_name, api_key=None):
        """
        If api_key is not provided, AirtableAuth will attempt
        to use os.environ['AIRTABLE_API_KEY']
        """
        session = requests.Session()
        session.auth = AirtableAuth(API_KEY=api_key)
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

    def get_records(self, **options):
        """
        Gets all records.

        Kwargs:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve
            # sort (``dict``): {'field': 'COLUMND_ID', 'direction':'desc'} | 'asc'

        Returns:
            records (``list``): List of Records

        >>> records = get_records(maxRecords=3, view='All')
        """
        records = []
        offset = None
        while True:
            response_data = self._get(self.url_table, offset=offset, **options)
            records.extend(response_data.get('records', []))
            offset = response_data.get('offset')
            if 'offset' not in response_data:
                break
        return records

    def get_match(self, field_name, field_value, **options):
        """
        Returns first match found in ``get_records()``

        Args:
            field_name (``str``)
            field_value (``str``)

        Kwargs:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve
            # sort (``dict``): {'field': 'COLUMND_ID', 'direction':'desc'} | 'asc'

        Returns:
            record (``dict``): First record to match the field_value provided
        """
        for record in self.get_records(**options):
            if record.get('fields', {}).get(field_name) == field_value:
                return record

    def get_search(self, field_name, field_value, **options):
        """
        Returns All matching records

        Args:
            field_name (``str``)
            field_value (``str``)

        Kwargs:
            view (``str``): Name of View
            maxRecords (``int``): Maximum number of records to retrieve
            # sort (``dict``): {'field': 'COLUMND_ID', 'direction':'desc'} | 'asc'

        Returns:
            record (``dict``)
        """
        records = []
        for record in self.get_records(**options):
            if record.get('fields', {}).get(field_name) == field_value:
                records.append(record)
        return records

    def insert(self, fields):
        """
        Inserts a record

        Args:
            fields(``dict``): Fields to add. Must be dictionary with Column names as Key

        Returns:
            record (``dict``)
        """
        return self._post(self.url_table, json_data={"fields": fields})

    def _batch_request(self, iterable, func):
        responses = []
        for item in iterable:
            responses.append(func(item))
            time.sleept(self.API_LIMIT)
        return responses

    def batch_insert(self, rows):
        """ Batch Insert without breaking API Rate Limit (5/sec) """
        self._batch_request(rows, self.insert)

    def update(self, record_id, fields):
        """
        Updates a record

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to add. Must be dictionary with Column names as Key

        Returns:
            record (``dict``)
        """
        record_url = self.record_url(record_id)
        return self._patch(record_url, json_data={"fields": fields})

    def update_by_field(self, field_name, field_value, fields, **options):
        """
        Updates a record

        Args:
            field_name(``str``): Name of the field to search
            field_value(``str``): Value to match
            fields(``dict``): Fields to add. Must be dictionary with Column names as Key

        Returns:
            record (``dict``)
        """
        record = self.get_match(field_name, field_value, **options)
        if record:
            record_url = self.record_url(record['id'])
            return self._patch(record_url, json_data={"fields": fields})

    def delete(self, record_id):
        record_url = self.record_url(record_id)
        return self._delete(record_url)

    def delete_by_field(self, field_name, field_value, **options):
        record = self.get_match(field_name, field_value, **options)
        record_url = self.record_url(record['id'])
        return self._delete(record_url)
