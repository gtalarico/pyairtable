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

For a full list of available methods see the :any:`Base` class below.
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
from .params import to_params_dict

# from .formulas import field_equals_value


class AirtableApi:
    VERSION = "v0"
    API_BASE_URL = "https://api.airtable.com/"
    API_LIMIT = 1.0 / 5  # 5 per second
    API_URL = posixpath.join(API_BASE_URL, VERSION)
    MAX_RECORDS_PER_REQUEST = 10

    def __init__(self, api_key, timeout=None):
        session = requests.Session()
        session.auth = AirtableAuth(api_key)
        self.session = session
        self.timeout = timeout

    @lru_cache()
    def get_table_url(self, base_id, table_name):
        """
        Args:

            base_id(``str``): Airtable base_id.
            table_name(``str``): Airtable table name. Value will be url encoded, so
                    use value as shown in Airtable.
        """
        url_safe_table_name = quote(table_name, safe="")
        table_url = posixpath.join(self.API_URL, base_id, url_safe_table_name)
        return table_url

    @lru_cache()
    def _get_record_url(self, base_id, table_name, record_id):
        """ Builds URL with record id """
        table_url = self.get_table_url(base_id, table_name)
        return posixpath.join(table_url, record_id)

    def _options_to_params(self, **options):
        """
        Process params names or values as needed using filters
        """
        # Does it need to be ordered + sorted ?
        # return {to_params_dict(name, value) for name, value in options.items()}
        params = {}
        for name, value in options.items():
            params.update(to_params_dict(name, value))
        return params

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

    def _request(self, method, url, params=None, json_data=None):
        response = self.session.request(
            method, url, params=params, json=json_data, timeout=self.timeout
        )
        return self._process_response(response)

    # def _get(self, url, **kwargs):
    #     processed_params = self._process_kwargs(**kwargs)
    #     return self._request("get", url, params=processed_params)

    # def _post(self, url, json_data):
    #     return self._request("post", url, json_data=json_data)

    # def _put(self, url, json_data):
    #     return self._request("put", url, json_data=json_data)

    # def _patch(self, url, json_data):
    #     return self._request("patch", url, json_data=json_data)

    # def _delete(self, url, params=None):
    #     return self._request("delete", url, params=params)

    def _get_record(self, base_id, table_name, record_id):
        """
        Retrieves a record by its id

        >>> record = airtable.get('recwPQIfs4wKPyc9D')

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Record
        """
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("get", record_url)

    def _get_iter(self, base_id, table_name, **options):
        # self, table_name, view="", page_size=None, fields=None, sort=None, formula=""
        """
        Record Retriever Iterator

        |max_records|

        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :any:`get_all`

        >>> for page in airtable.get_iter():
        ...     for record in page:
        ...         print(record)
        [{'fields': ... }, ...]


        |view|
        |page_size|
        |fields|
        |sort|
        |formula|

        Returns:
            iterator (``list``): List of Records, grouped by pageSize

        """
        offset = None
        params = self._options_to_params(**options)
        while True:
            table_url = self.get_table_url(base_id, table_name)
            if offset:
                params.update({"offset": offset})
            data = self._request("get", table_url, params=params)
            records = data.get("records", [])
            time.sleep(self.API_LIMIT)
            yield records
            offset = data.get("offset")
            if not offset:
                break

    def _first(self, base_id, table_name, **options):
        for records in self._get_iter(base_id, table_name, max_records=1, **options):
            for record in records:
                return record

    def _get_all(self, base_id, table_name, **options):
        """
            Retrieves all records repetitively and returns a single list.

            >>> airtable.get_all()
            >>> airtable.get_all(view='MyView', fields=['ColA', '-ColB'])
            >>> airtable.get_all(maxRecords=50)
            [{'fields': ... }, ...]


        Keyword Args:
                |max_records|
                |view|
                |fields|
                |sort|
                |formula|

            Returns:
                records (``list``): List of Records

            >>> records = get_all(maxRecords=3, view='All')

        """
        all_records = []

        for records in self._get_iter(base_id, table_name, **options):
            all_records.extend(records)
        return all_records

    def _create(self, base_id, table_name, fields, typecast=False):
        """
        Creates a new record

        >>> record = {'Name': 'John'}
        >>> airtable.create(record)

        Args:
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.

        Keyword Args:
            |typecast|

        Returns:
            record (``dict``): Inserted record

        """

        table_url = self.get_table_url(base_id, table_name)
        return self._request(
            "post",
            table_url,
            json_data={"fields": fields, "typecast": typecast},
        )

    def _batch_create(self, base_id, table_name, records, typecast=False):
        """
        Breaks records into chunks of 10 and inserts them in batches.
        Follows the set API rate.
        To change the rate limit use ``airtable.API_LIMIT = 0.2``
        (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert(records)

        Args:
            records(``list``): Records to insert

        Keyword Args:
            |typecast|

        Returns:
            records (``list``): list of added records
        """
        table_url = self.get_table_url(base_id, table_name)
        inserted_records = []
        for chunk in self._chunk(records, self.MAX_RECORDS_PER_REQUEST):
            new_records = self._build_batch_record_objects(chunk)
            response = self._request(
                "post",
                table_url,
                json_data={"records": new_records, "typecast": typecast},
            )
            inserted_records += response["records"]
            time.sleep(self.API_LIMIT)
        return inserted_records

    def _update(
        self,
        base_id: str,
        table_name: str,
        record_id: str,
        fields: dict,
        replace=False,
        typecast=False,
    ):
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

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            |typecast|

        Returns:
            record (``dict``): Updated record
        """
        record_url = self._get_record_url(base_id, table_name, record_id)

        method = "put" if replace else "patch"
        return self._request(
            method, record_url, json_data={"fields": fields, "typecast": typecast}
        )

    def _batch_update(
        self,
        base_id: str,
        table_name: str,
        records: List[dict],
        replace=False,
        typecast=False,
    ):
        """
        Updates a records by their record id's in batch.

        Args:
            records(``list``): List of dict: [{"id": record_id, "field": fields_to_update_dict}]

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            |typecast|

        Returns:
            records(``list``): list of updated records
        """
        updated_records = []
        table_url = self.get_table_url(base_id, table_name)
        method = "put" if replace else "patch"
        for records in self._chunk(records, self.MAX_RECORDS_PER_REQUEST):
            chunk_records = [{"id": x["id"], "fields": x["fields"]} for x in records]
            response = self._request(
                method,
                table_url,
                json_data={"records": chunk_records, "typecast": typecast},
            )
            updated_records += response["records"]
        #
        return updated_records

    def _delete(self, base_id: str, table_name: str, record_id: str):
        """
        Deletes a record by its id

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> airtable.delete(record['id'])

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Deleted Record
        """
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("delete", record_url)

    def _batch_delete(self, base_id: str, table_name: str, record_ids: List[str]):
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
        table_url = self.get_table_url(base_id, table_name)
        for record_ids in self._chunk(record_ids, self.MAX_RECORDS_PER_REQUEST):
            delete_results = self._request(
                "delete", table_url, params={"records[]": record_ids}
            )
            deleted_records.extend(delete_results["records"])
            time.sleep(self.API_LIMIT)
        return deleted_records

    def __repr__(self) -> str:
        return "<Airtable Api>"
