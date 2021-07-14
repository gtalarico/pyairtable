"""

Airtable Class Instance
***********************

>>> airtable = Airtable('base_id', 'table_name')
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

>>> airtable.search('ColumnA', 'SearchValue')

Formulas:

>>> airtable.get_all(formula="FIND('DUP', {COLUMN_STR})=1")


Insert:

>>> airtable.insert({'First Name': 'John'})

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

from typing import List
import requests
from collections import OrderedDict
from functools import lru_cache
import posixpath
import time
from urllib.parse import quote

from .auth import AirtableAuth
from .params import get_param_dict
from .formulas import field_equals_value


class Base(object):

    VERSION = "v0"
    API_BASE_URL = "https://api.airtable.com/"
    API_LIMIT = 1.0 / 5  # 5 per second
    API_URL = posixpath.join(API_BASE_URL, VERSION)
    MAX_RECORDS_PER_REQUEST = 10

    def __init__(self, base_id, api_key, timeout=None):
        """
        Instantiates a new Airtable Base instance

        >>> table = Airtable('base_id', 'api_key')

        With timeout:

        >>> table = Airtable('base_id', 'tablename', timeout=(1, 1))

        Args:
            base_id(``str``): Airtable base identifier
            api_key (``str``): API key.

        Keyword Args:
            timeout (``int``, ``Tuple[int, int]``, optional): Optional timeout
                parameters to be used in request. `See requests timeout docs.
                <https://requests.readthedocs.io/en/master/user/advanced/#timeouts>`_

        """
        session = requests.Session()
        session.auth = AirtableAuth(api_key=api_key)
        self.session = session
        self.base_id = base_id
        self.timeout = timeout

    @lru_cache()
    def table_url(self, table_name):
        """
        table_name(``str``): Airtable table name. Value will be url encoded, so
                use value as shown in Airtable.
        """
        url_safe_table_name = quote(table_name, safe="")
        table_url = posixpath.join(self.API_URL, self.base_id, url_safe_table_name)
        return table_url

    def _process_params(self, params):
        """
        Process params names or values as needed using filters
        """
        new_params = OrderedDict()
        for param_name, param_value in sorted(params.items()):
            params_dict = get_param_dict(param_name, param_value)
            new_params.update(params_dict)
        return new_params

    def _chunk(self, iterable, chunk_size):
        """ Break iterable into chunks """
        for i in range(0, len(iterable), chunk_size):
            yield iterable[i : i + chunk_size]

    def _build_batch_record_objects(self, records):
        return [{"fields": record} for record in records]

    def _process_response(self, response):
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            err_msg = str(exc)

            # Attempt to get Error message from response, Issue #16
            try:
                error_dict = response.json()
            except ValueError:
                pass
            else:
                if "error" in error_dict:
                    err_msg += " [Error: {}]".format(error_dict["error"])
            exc.args = (*exc.args, err_msg)
            raise exc
        else:
            return response.json()

    @lru_cache
    def record_url(self, table_url, record_id):
        """ Builds URL with record id """
        return posixpath.join(table_url, record_id)

    def _request(self, method, url, params=None, json_data=None):
        response = self.session.request(
            method, url, params=params, json=json_data, timeout=self.timeout
        )
        return self._process_response(response)

    def _get(self, url, **params):
        processed_params = self._process_params(params)
        return self._request("get", url, params=processed_params)

    def _post(self, url, json_data):
        return self._request("post", url, json_data=json_data)

    def _put(self, url, json_data):
        return self._request("put", url, json_data=json_data)

    def _patch(self, url, json_data):
        return self._request("patch", url, json_data=json_data)

    def _delete(self, url, params=None):
        return self._request("delete", url, params=params)

    def get(self, table_name, record_id):
        """
        Retrieves a record by its id

        >>> record = airtable.get('recwPQIfs4wKPyc9D')

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Record
        """
        record_url = self.record_url(table_name, record_id)
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
                max_records (``int``, optional): The maximum total number of
                    records that will be returned. See :any:`MaxRecordsParam`
                view (``str``, optional): The name or ID of a view.
                    See :any:`ViewParam`.
                page_size (``int``, optional ): The number of records returned
                    in each request. Must be less than or equal to 100.
                    Default is 100. See :any:`PageSizeParam`.
                fields (``str``, ``list``, optional): Name of field or fields  to
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
            records = data.get("records", [])
            time.sleep(self.API_LIMIT)
            yield records
            offset = data.get("offset")
            if not offset:
                break

    def get_all(self, table_name, **options):
        """
            Retrieves all records repetitively and returns a single list.

            >>> airtable.get_all()
            >>> airtable.get_all(view='MyView', fields=['ColA', '-ColB'])
            >>> airtable.get_all(maxRecords=50)
            [{'fields': ... }, ...]


        Keyword Args:
                max_records (``int``, optional): The maximum total number of
                    records that will be returned. See :any:`MaxRecordsParam`
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

    def search(self, table_name, field_name, field_value, record=None, **options):
        """
        Returns all matching records found in :any:`get_all`

        >>> airtable.search('Gender', 'Male')
        [{'fields': {'Name': 'John', 'Gender': 'Male'}, ... ]

        >>> airtable.search('Checkbox Field', 1)
        [{'fields': {'Name': 'John', 'Gender': 'Male'}, ... ]

        Args:
            field_name (``str``): Name of field to match (column name).
            field_value (``str``): Value of field to match.

        Keyword Args:
            max_records (``int``, optional): The maximum total number of
                records that will be returned. See :any:`MaxRecordsParam`
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
        formula = field_equals_value(field_name, field_value)
        options["formula"] = formula
        records = self.get_all(table_name, **options)
        return records

    def create(self, table_name, fields, typecast=False):
        """
        Creates a new record

        >>> record = {'Name': 'John'}
        >>> airtable.create(record)

        Args:
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            record (``dict``): Inserted record

        """

        return self._post(
            self.table_url(table_name),
            json_data={"fields": fields, "typecast": typecast},
        )

    def batch_create(self, table_name, records, typecast=False):
        """
        Breaks records into chunks of 10 and inserts them in batches.
        Follows the set API rate.
        To change the rate limit use ``airtable.API_LIMIT = 0.2``
        (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert(records)

        Args:
            records(``list``): Records to insert
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            records (``list``): list of added records
        """
        table_url = self.table_url(table_name)
        inserted_records = []
        for chunk in self._chunk(records, self.MAX_RECORDS_PER_REQUEST):
            new_records = self._build_batch_record_objects(chunk)
            response = self._post(
                table_url, json_data={"records": new_records, "typecast": typecast}
            )
            inserted_records += response["records"]
            time.sleep(self.API_LIMIT)
        return inserted_records

    def update(self, table_name: str, record_id: str, fields: dict, typecast=False):
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
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            record (``dict``): Updated record
        """
        record_url = self.record_url(table_name, record_id)
        return self._patch(
            record_url, json_data={"fields": fields, "typecast": typecast}
        )

    def batch_update(self, table_name: str, records: List[dict], typecast=False):
        """
        Updates a records by their record id's in batch.

        Args:
            records(``list``): List of dict: [{"id": record_id, "field": fields_to_update_dict}]
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            records(``list``): list of updated records
        """
        updated_records = []
        for records in self._chunk(records, self.MAX_RECORDS_PER_REQUEST):
            chunk_records = [{"id": x["id"], "fields": x["fields"]} for x in records]
            response = self._patch(
                self.url_table,
                json_data={"records": chunk_records, "typecast": typecast},
            )
            updated_records += response["records"]
        #
        return updated_records

    def replace(self, table_name: str, record_id: str, fields: dict, typecast=False):
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
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            record (``dict``): New record
        """
        record_url = self.record_url(table_name, record_id)
        return self._put(record_url, json_data={"fields": fields, "typecast": typecast})

    def delete(self, record_id: str):
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

    def batch_delete(self, record_ids: List[str]):
        """
        Breaks records into batches of 10 and deletes in batches, following set
        API Rate Limit (5/sec).
        To change the rate limit set value of ``airtable.API_LIMIT`` to
        the time in seconds it should sleep before calling the function again.

        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> airtable.batch_delete(records_ids)

        Args:
            records(``list``): Record Ids to delete

        Returns:
            records(``list``): list of records deleted

        """
        deleted_records = []
        url = self.url_table
        for record_ids in self._chunk(record_ids, self.MAX_RECORDS_PER_REQUEST):
            deleted_records += self._delete(url, params={"records[]": record_ids})
            time.sleep(self.API_LIMIT)
        return deleted_records

    def __repr__(self) -> str:
        return "<Base id={}>".format(self.base_id)
