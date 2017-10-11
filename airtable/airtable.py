"""

Airtable Class Instance
***********************

>>> airtable = Airtable('base_key', 'table_name')
>>> airtable.get_all()
[{id:'rec123asa23', fields': {'Column': 'Value'}, ...}]

For more information on Api Key and authentication see
the :doc:`authentication`.

------------------------------------------------------------------------

Examples
********

For a full list of available methods see the :any:`Airtable` class below.
For more details on the Parameter filters see the documentation on the
available :doc:`params` as well as the
`Airtable API Docs <http://airtable.com/api>`_

Record/Page Iterator:

>>> for page in airtable.get_iter(view='ViewName',sort='COLUMN_A'):
...     for record in page:
...         value = record['fields']['COLUMN_A']

Get all Records:

>>> airtable.get_all(view='ViewName',sort='COLUMN_A')
[{id:'rec123asa23', 'fields': {'COLUMN_A': 'Value', ...}, ... ]

Search:

>>> airtable.search('ColumnA', 'SeachValue')

Formulas:

>>> airtable.get_all(formula="FIND('DUP', {COLUMN_STR})=1")


Insert:

>>> airtable.insert({'First Name', 'John'})

Delete:

>>> airtable.delete('recwPQIfs4wKPyc9D')


You can see the Airtable Class in action in this
`Jupyter Notebook <https://github.com/gtalarico/airtable-python-wrapper/blob/master/Airtable.ipynb>`_

------------------------------------------------------------------------

Return Values
**************

Return Values: when records are returned,
they will most often be a list of Airtable records (dictionary) in a format
similar to this:

>>> [{
...     "records": [
...         {
...             "id": "recwPQIfs4wKPyc9D",
...             "fields": {
...                 "COLUMN_ID": "1",
...             },
...             "createdTime": "2017-03-14T22:04:31.000Z"
...         },
...         {
...             "id": "rechOLltN9SpPHq5o",
...             "fields": {
...                 "COLUMN_ID": "2",
...             },
...             "createdTime": "2017-03-20T15:21:50.000Z"
...         },
...         {
...             "id": "rec5eR7IzKSAOBHCz",
...             "fields": {
...                 "COLUMN_ID": "3",
...             },
...             "createdTime": "2017-08-05T21:47:52.000Z"
...         }
...     ],
...     "offset": "rec5eR7IzKSAOBHCz"
... }, ... ]

"""  #

import os
import json
import requests
from requests.exceptions import HTTPError
import posixpath
import time
from six.moves.urllib.parse import unquote
from six.moves.urllib.parse import quote

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
        self.table_name = table_name
        urlsafe_table_name = quote(table_name, safe='')
        self.url_table = posixpath.join(self.API_URL, base_key,
                                        urlsafe_table_name)
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
            ParamClass = AirtableParams._get(param_name)
            new_param = ParamClass(param_value).to_param_dict()
            params.update(new_param)
        return params

    def _process_response(self, response):
        # Removed due to IronPython Bug
        # https://github.com/IronLanguages/ironpython2/issues/242
        # if response.status_code == 422:
        #     raise HTTPError('Unprocessable Entity for url(
        #                        decoded): {}'.format(unquote(response.url)))
        response.raise_for_status()
        return response.json()

    def record_url(self, record_id):
        """ Builds URL with record id """
        return posixpath.join(self.url_table, record_id)

    def _request(self, method, url, params=None, json_data=None):
        response = self.session.request(method, url, params=params, json=json_data)
        # self._dump_request_data(response)
        return self._process_response(response)

    # def _dump_request_data(self, response):
    #     """ For Debugging """
    #     timestamp = str(time.time()).split('.')[-1]
    #     url = response.request.url
    #     method = response.request.method
    #     response_json = response.json()
    #     status = response.status_code
    #     filepath = os.path.join('tests', 'dump', '{}-{}_{}.json'.format(
    #                                                                 method,
    #                                                                 status,
    #                                                                 timestamp))
    #     dump = {
    #             'url': url,
    #             'method': method,
    #             'response_json': response_json,
    #             }
    #     with open(filepath, 'w') as fp:
    #         json.dump(dump, fp, indent=4)


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

        >>> for page in airtable.get_iter():
        ...     for record in page:
        ...         print(record)
        [{'fields': ... }, ...]

        Keyword Args:
            maxRecords (``int``, optional): The maximum total number of records
                that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            pageSize (``int``, optional ): The number of records returned
                in each request. Must be less than or equal to 100.
                Default is 100. See :any:`PageSizeParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.
            formula (``str``, optional): Airtable formula.
                See :any:`FormulaParam`.

        Returns:
            iterator (``list``): List of Records, grouped by pageSize

        """
        offset = None
        while True:
            data = self._get(self.url_table, offset=offset, **options)
            records = data.get('records', [])
            time.sleep(self.API_LIMIT)
            yield records
            offset = data.get('offset')
            if not offset:
                break

    def get_all(self, **options):
        """
        Retrieves all records repetitively and returns a single list.

        >>> airtable.get_all()
        >>> airtable.get_all(view='MyView', fields=['ColA', '-ColB'])
        >>> airtable.get_all(maxRecords=50)
        [{'fields': ... }, ...]

        Keyword Args:
            maxRecords (``int``, optional): The maximum total number of records
                that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.
            formula (``str``, optional): Airtable formula.
                See :any:`FormulaParam`.

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
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.

        Keyword Args:
            maxRecords (``int``, optional): The maximum total number of records
                that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            record (``dict``): First record to match the field_value provided
        """
        formula = self.formula_from_name_and_value(field_name, field_value)
        options['formula'] = formula
        for record in self.get_all(**options):
            return record
        else:
             return {}

    def search(self, field_name, field_value, record=None, **options):
        """
        Returns all matching records found in :any:`get_all`

        >>> airtable.search('Gender', 'Male')
        [{'fields': {'Name': 'John', 'Gender': 'Male'}, ... ]

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.

        Keyword Args:
            maxRecords (``int``, optional): The maximum total number of records
                that will be returned. See :any:`MaxRecordsParam`
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            fields (``str``, ``list``, optional): Name of field or fields to
                be retrieved. Default is all fields. See :any:`FieldsParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            records (``list``): All records that matched ``field_value``

        """
        records = []
        formula = self.formula_from_name_and_value(field_name, field_value)
        options['formula'] = formula
        records = self.get_all(**options)
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
        To change the rate limit use ``airtable.API_LIMIT = 0.2``
        (5 per second)

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
        Updates a record by its record id.
        Only Fields passed are updated, the rest are left as is.

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
        Updates the first record to match field name and value.
        Only Fields passed are updated, the rest are left as is.

        >>> record = {'Name': 'John', 'Tel': '540-255-5522'}
        >>> airtable.update_by_field('Name', 'John', record)

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

        Returns:
            record (``dict``): Updated record
        """
        record = self.match(field_name, field_value, **options)
        return {} if not record else self.update(record['id'], fields)

    def replace(self, record_id, fields):
        """
        Replaces a record by its record id.
        All Fields are updated to match the new ``fields`` provided.
        If a field is not included in ``fields``, value will bet set to null.
        To update only selected fields, use :any:`update`.

        >>> record = airtable.match('Seat Number', '22A')
        >>> fields = {'PassangerName': 'Mike', 'Passport': 'YASD232-23'}
        >>> airtable.replace(record['id'], fields)

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to replace with.
                Must be dictionary with Column names as Key.

        Returns:
            record (``dict``): New record
        """
        record_url = self.record_url(record_id)
        return self._put(record_url, json_data={"fields": fields})

    def replace_by_field(self, field_name, field_value, fields, **options):
        """
        Replaces the first record to match field name and value.
        All Fields are updated to match the new ``fields`` provided.
        If a field is not included in ``fields``, value will bet set to null.
        To update only selected fields, use :any:`update`.

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.
            fields(``dict``): Fields to replace with.
                Must be dictionary with Column names as Key.

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

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
        Deletes first record  to match provided ``field_name`` and
        ``field_value``.

        >>> record = airtable.delete_by_field('Employee Id', 'DD13332454')

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                See :any:`ViewParam`.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending. See :any:`SortParam`.

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
            maxRecords (``int``, optional): The maximum total number of records
                that will be returned. See :any:`MaxRecordsParam`
            maxRecords (``int``, optional): Maximum number of records to retrieve

        Returns:
            records (``tuple``): (new_records, deleted_records)
        """

        all_record_ids = [r['id'] for r in self.get_all(**options)]
        deleted_records = self.batch_delete(all_record_ids)
        new_records = self.batch_insert(records)
        return (new_records, deleted_records)

    @staticmethod
    def formula_from_name_and_value(field_name, field_value):
        """ Creates a formula to match cells from from field_name and value """
        if isinstance(field_value, str):
            field_value = "'{}'".format(field_value)

        formula = "{{{name}}}={value}".format(name=field_name,
                                              value=field_value)
        return formula

    def __repr__(self):
        return '<Airtable table:{}>'.format(self.table_name)
