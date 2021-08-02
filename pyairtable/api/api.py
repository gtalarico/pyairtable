import abc
from functools import lru_cache
import posixpath
from typing import List, Optional
import time
from urllib.parse import quote

import requests

from .auth import AirtableAuth
from .params import to_params_dict


class ApiBase(metaclass=abc.ABCMeta):
    VERSION = "v0"
    API_BASE_URL = "https://api.airtable.com/"
    API_LIMIT = 1.0 / 5  # 5 per second
    API_URL = posixpath.join(API_BASE_URL, VERSION)
    MAX_RECORDS_PER_REQUEST = 10

    def __init__(self, api_key: str, timeout=None):
        session = requests.Session()
        session.auth = AirtableAuth(api_key)
        self.session = session
        self.timeout = timeout

    @lru_cache()
    def get_table_url(self, base_id: str, table_name: str):
        url_safe_table_name = quote(table_name, safe="")
        table_url = posixpath.join(self.API_URL, base_id, url_safe_table_name)
        return table_url

    @lru_cache()
    def _get_record_url(self, base_id: str, table_name: str, record_id):
        """Builds URL with record id"""
        table_url = self.get_table_url(base_id, table_name)
        return posixpath.join(table_url, record_id)

    def _options_to_params(self, **options):
        """
        Process params names or values as needed using filters
        """
        params = {}
        for name, value in options.items():
            params.update(to_params_dict(name, value))
        return params

    def _chunk(self, iterable, chunk_size):
        """Break iterable into chunks"""
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

    def _request(self, method: str, url: str, params=None, json_data=None):
        response = self.session.request(
            method, url, params=params, json=json_data, timeout=self.timeout
        )
        return self._process_response(response)

    def _get_record(self, base_id: str, table_name: str, record_id: str) -> dict:
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("get", record_url)

    def _iterate(self, base_id: str, table_name: str, **options):
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

    def _first(self, base_id: str, table_name: str, **options) -> Optional[dict]:
        for records in self._iterate(
            base_id, table_name, page_size=1, max_records=1, **options
        ):
            for record in records:
                return record
        return None

    def _all(self, base_id: str, table_name: str, **options) -> List[dict]:
        all_records = []

        for records in self._iterate(base_id, table_name, **options):
            all_records.extend(records)
        return all_records

    def _create(self, base_id: str, table_name: str, fields: dict, typecast=False):

        table_url = self.get_table_url(base_id, table_name)
        return self._request(
            "post",
            table_url,
            json_data={"fields": fields, "typecast": typecast},
        )

    def _batch_create(
        self, base_id: str, table_name: str, records: List[dict], typecast=False
    ) -> List[dict]:

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
    ) -> List[dict]:
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

        return updated_records

    def _delete(self, base_id: str, table_name: str, record_id: str):
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("delete", record_url)

    def _batch_delete(
        self, base_id: str, table_name: str, record_ids: List[str]
    ) -> List[dict]:
        deleted_records = []
        table_url = self.get_table_url(base_id, table_name)
        for record_ids in self._chunk(record_ids, self.MAX_RECORDS_PER_REQUEST):
            delete_results = self._request(
                "delete", table_url, params={"records[]": record_ids}
            )
            deleted_records.extend(delete_results["records"])
            time.sleep(self.API_LIMIT)
        return deleted_records


class Api(ApiBase):
    """
    Represents an Airtable Api.

    The Api Key is provided on init and ``base_id`` and ``table_id``
    can be provided on each method call.

    If you are only operating on one Table, or one Base, consider using
    :class:`Base` or :class:`Table`.

    Usage:
        >>> api = Api('apikey')
        >>> api.all('base_id', 'table_name')
    """

    def __init__(self, api_key: str, timeout=None):
        """

        Args:
            api_key: |arg_api_key|

        Keyword Args:
            timeout(``Tuple``): |arg_timeout|

        """
        super().__init__(api_key, timeout=timeout)

    def get_record_url(self, base_id: str, table_name: str, record_id: str):
        """
        Returns a url for the provided record

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|

        """
        return super()._get_record_url(base_id, table_name, record_id)

    def get(self, base_id: str, table_name: str, record_id: str):
        """
        Retrieves a record by its id

        >>> record = api.get('base_id', 'table_name', 'recwPQIfs4wKPyc9D')

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            record_id: |arg_record_id|

        Returns:
            record: Record
        """
        return super()._get_record(base_id, table_name, record_id)

    def iterate(self, base_id: str, table_name: str, **options):
        """
        Record Retriever Iterator

        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :meth:`all`

        >>> for page in api.iterate('base_id', 'table_name'):
        ...     for record in page:
        ...         print(record)
        {"id": ... }
        ...

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|

        Keyword Args:
            view: |kwarg_view|
            page_size: |kwarg_page_size|
            max_records: |kwarg_max_records|
            fields: |kwarg_fields|
            sort: |kwarg_sort|
            formula: |kwarg_formula|

        Returns:
            iterator: Record Iterator, grouped by page size

        """
        gen = super()._iterate(base_id, table_name, **options)
        for i in gen:
            yield i

    def first(self, base_id: str, table_name: str, **options):
        """
        Retrieves the first found record or ``None`` if no records are returned.

        This is similar to :meth:`~pyairtable.api.api.Api.all`, except it
        it sets ``page_size`` and ``max_records`` to ``1`` to optimize query.

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
        """
        return super()._first(base_id, table_name, **options)

    def all(self, base_id: str, table_name: str, **options):
        """
        Retrieves all records repetitively and returns a single list.

        >>> api.all('base_id', 'table_name', view='MyView', fields=['ColA', '-ColB'])
        [{'fields': ... }, ...]
        >>> api.all('base_id', 'table_name', maxRecords=50)
        [{'fields': ... }, ...]

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|

        Keyword Args:
            view: |kwarg_view|
            page_size: |kwarg_page_size|
            max_records: |kwarg_max_records|
            fields: |kwarg_fields|
            sort: |kwarg_sort|
            formula: |kwarg_formula|

        Returns:
            records (``list``): List of Records

        >>> records = all(maxRecords=3, view='All')

        """
        return super()._all(base_id, table_name, **options)

    def create(self, base_id: str, table_name: str, fields: dict, typecast=False):
        """
        Creates a new record

        >>> record = {'Name': 'John'}
        >>> api.create('base_id', 'table_name', record)

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.

        Keyword Args:
            typecast: |kwarg_typecast|

        Returns:
            record (``dict``): Inserted record

        """
        return super()._create(base_id, table_name, fields, typecast=typecast)

    def batch_create(self, base_id: str, table_name: str, records, typecast=False):
        """
        Breaks records into chunks of 10 and inserts them in batches.
        Follows the set API rate.
        To change the rate limit you can change ``API_LIMIT = 0.2``
        (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> api.batch_insert('base_id', 'table_name', records)

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            records(``List[dict]``): List of dictionaries representing
                records to be created.

        Keyword Args:
            typecast: |kwarg_typecast|

        Returns:
            records (``list``): list of added records
        """
        return super()._batch_create(base_id, table_name, records, typecast=typecast)

    def update(
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

        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
        {id:'recwPQIfs4wKPyc9D', fields': {"First Name": "John", "Age": 21}}
        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21}, replace=True)
        {id:'recwPQIfs4wKPyc9D', fields': {"Age": 21}}

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            record_id: |arg_record_id|
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            typecast: |kwarg_typecast|

        Returns:
            record (``dict``): Updated record
        """

        return super()._update(
            base_id,
            table_name,
            record_id,
            fields,
            replace=replace,
            typecast=typecast,
        )

    def batch_update(
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
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            records(``list``): List of dict: [{"id": record_id, "field": fields_to_update_dict}]

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            typecast: |kwarg_typecast|

        Returns:
            records(``list``): list of updated records
        """
        return super()._batch_update(
            base_id, table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, base_id: str, table_name: str, record_id: str):
        """
        Deletes a record by its id

        >>> record = api.match('base_id', 'table_name', 'Employee Id', 'DD13332454')
        >>> api.delete('base_id', 'table_name', record['id'])

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            record_id: |arg_record_id|

        Returns:
            record (``dict``): Deleted Record
        """
        return super()._delete(base_id, table_name, record_id)

    def batch_delete(self, base_id: str, table_name: str, record_ids: List[str]):
        """
        Breaks records into batches of 10 and deletes in batches, following set
        API Rate Limit (5/sec).
        To change the rate limit set value of ``API_LIMIT`` to
        the time in seconds it should sleep before calling the function again.

        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> api.batch_delete('base_id', 'table_name', records_ids)

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            record_ids(``list``): Record Ids to delete

        Returns:
            records(``list``): list of records deleted

        """
        return super()._batch_delete(base_id, table_name, record_ids)

    def __repr__(self) -> str:
        return "<Airtable Api>"
