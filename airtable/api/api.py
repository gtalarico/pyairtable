from typing import List, Optional
import requests
from functools import lru_cache
import posixpath
import time
from urllib.parse import quote

from .auth import AirtableAuth
from .params import to_params_dict


class AirtableApi:
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
        """
        Args:

            base_id: Airtable base_id.
            table_name: Airtable table name. Value will be url encoded, so
                use value as shown in Airtable.
        """
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
        # Does it need to be ordered + sorted ?
        # return {to_params_dict(name, value) for name, value in options.items()}
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
        """
        Retrieves a record by its id

        >>> record = airtable.get('recwPQIfs4wKPyc9D')

        Args:
            base_id: Airtable base id.
            table_name: Airtable table name. Table name should be unencoded,
                as shown on browser.
            record_id: Airtable record id

        Returns:
            record: Record
        """
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("get", record_url)

    def _iterate(self, base_id: str, table_name: str, **options):
        # self, table_name, view="", page_size=None, fields=None, sort=None, formula=""
        """
        Record Retriever Iterator


        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :any:`_get_all`

        >>> for page in airtable.get_iter():
        ...     for record in page:
        ...         print(record)
        [{'fields': ... }, ...]


        Args:
            base_id: Airtable base id.
            table_name: Airtable table name. Table name should be unencoded,
                as shown on browser.

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                If set, only the records in that view will be returned.
                The records will be sorted according to the order of the view.
            page_size (``int``, optional ): The number of records returned
                in each request. Must be less than or equal to 100.
                Default is 100.
            max_records (``int``, optional): The maximum total number of
                records that will be returned.
            fields (``str``, ``list``, optional): Name of field or fields  to
                be retrieved. Default is all fields.
                Only data for fields whose names are in this list will be included in
                the records. If you don't need every field, you can use this parameter
                to reduce the amount of data transferred.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending.
                This parameter specifies how the records will be ordered. If you set the view
                parameter, the returned records in that view will be sorted by these
                fields.

                If sorting by multiple columns, column names can be passed as a list.
                Sorting Direction is ascending by default, but can be reversed by
                prefixing the column name with a minus sign ``-``.
            formula (``str``, optional): An Airtable formula.
                The formula will be evaluated for each record, and if the result
                is not 0, false, "", NaN, [], or #Error! the record will be included
                in the response.

                If combined with view, only records in that view which satisfy the
                formula will be returned. For example, to only include records where
                ``COLUMN_A`` isn't empty, pass in: ``"NOT({COLUMN_A}='')"``

                For more information see
                    `Airtable Docs on formulas. <https://airtable.com/api>`_

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

    def _first(self, base_id: str, table_name: str, **options) -> Optional[dict]:
        for records in self._iterate(base_id, table_name, max_records=1, **options):
            for record in records:
                return record
        return None

    def _get_all(self, base_id: str, table_name: str, **options) -> List[dict]:
        """
        Retrieves all records repetitively and returns a single list.

        >>> airtable.get_all()
        >>> airtable.get_all(view='MyView', fields=['ColA', '-ColB'])
        >>> airtable.get_all(maxRecords=50)
        [{'fields': ... }, ...]

        Args:
            base_id: Airtable base id.
            table_name(``str``): Airtable table name. Table name should be unencoded,
                as shown on browser.

        Keyword Args:
            view (``str``, optional): The name or ID of a view.
                If set, only the records in that view will be returned.
                The records will be sorted according to the order of the view.
            page_size (``int``, optional ): The number of records returned
                in each request. Must be less than or equal to 100.
                Default is 100.
            max_records (``int``, optional): The maximum total number of
                records that will be returned.
            fields (``str``, ``list``, optional): Name of field or fields  to
                be retrieved. Default is all fields.
                Only data for fields whose names are in this list will be included in
                the records. If you don't need every field, you can use this parameter
                to reduce the amount of data transferred.
            sort (``list``, optional): List of fields to sort by.
                Default order is ascending.
                This parameter specifies how the records will be ordered. If you set the view
                parameter, the returned records in that view will be sorted by these
                fields.

                If sorting by multiple columns, column names can be passed as a list.
                Sorting Direction is ascending by default, but can be reversed by
                prefixing the column name with a minus sign ``-``.
            formula (``str``, optional): An Airtable formula.
                The formula will be evaluated for each record, and if the result
                is not 0, false, "", NaN, [], or #Error! the record will be included
                in the response.

                If combined with view, only records in that view which satisfy the
                formula will be returned. For example, to only include records where
                ``COLUMN_A`` isn't empty, pass in: ``"NOT({COLUMN_A}='')"``

                For more information see
                    `Airtable Docs on formulas. <https://airtable.com/api>`_

        Returns:
            records (``list``): List of Records

        >>> records = get_all(maxRecords=3, view='All')

        """
        all_records = []

        for records in self._iterate(base_id, table_name, **options):
            all_records.extend(records)
        return all_records

    def _create(self, base_id: str, table_name: str, fields: dict, typecast=False):
        """
        Creates a new record

        >>> record = {'Name': 'John'}
        >>> airtable.create(record)

        Args:
            base_id: Airtable base id.
            table_name(``str``): Airtable table name. Table name should be unencoded,
                as shown on browser.
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.

        Keyword Args:
            typecast(``boolean``): Automatic data conversion from string values.

        Returns:
            record (``dict``): Inserted record

        """

        table_url = self.get_table_url(base_id, table_name)
        return self._request(
            "post",
            table_url,
            json_data={"fields": fields, "typecast": typecast},
        )

    def _batch_create(
        self, base_id: str, table_name: str, records: List[dict], typecast=False
    ) -> List[dict]:
        """
        Breaks records into chunks of 10 and inserts them in batches.
        Follows the set API rate.
        To change the rate limit use ``airtable.API_LIMIT = 0.2``
        (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert(records)

        Args:
            base_id: Airtable base id.
            table_name: Airtable table name. Table name should be unencoded,
                as shown on browser.
            records: List of records to be created

        Keyword Args:
            typecast(): Automatic data conversion from string values.

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
    ) -> List[dict]:
        """
        Updates a record by its record id.
        Only Fields passed are updated, the rest are left as is.

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> fields = {'Status': 'Fired'}
        >>> airtable.update(record['id'], fields)

        Args:
            base_id: Airtable base id.
            table_name(``str``): Airtable table name. Table name should be unencoded,
                as shown on browser.
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            typecast(``boolean``): Automatic data conversion from string values.

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
            base_id: Airtable base id.
            table_name(``str``): Airtable table name. Table name should be unencoded,
                as shown on browser.
            records(``list``): List of dict: [{"id": record_id, "field": fields_to_update_dict}]

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            typecast(``boolean``): Automatic data conversion from string values.

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

        return updated_records

    def _delete(self, base_id: str, table_name: str, record_id: str):
        """
        Deletes a record by its id

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> airtable.delete(record['id'])

        Args:
            base_id: Airtable base id.
            table_name(``str``): Airtable table name. Table name should be unencoded,
                as shown on browser.
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Deleted Record
        """
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("delete", record_url)

    def _batch_delete(
        self, base_id: str, table_name: str, record_ids: List[str]
    ) -> List[dict]:
        """
        Breaks records into batches of 10 and deletes in batches, following set
        API Rate Limit (5/sec).
        To change the rate limit set value of ``airtable.API_LIMIT`` to
        the time in seconds it should sleep before calling the function again.

        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> airtable.batch_delete(records_ids)

        Args:
            base_id: Airtable base id.
            table_name(``str``): Airtable table name. Table name should be unencoded,
                as shown on browser.
            record_ids(``list``): Record Ids to delete

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
