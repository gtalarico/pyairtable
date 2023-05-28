import urllib.parse
from typing import Any, Iterator, List, Optional

from typing_extensions import Self as SelfType

import pyairtable.api.api
import pyairtable.api.base
from pyairtable.api.types import (
    FieldName,
    Fields,
    RecordDeletedDict,
    RecordDict,
    RecordId,
    UpdateRecordDict,
    assert_typed_dict,
    assert_typed_dicts,
)


class Table:
    """
    Represents an Airtable table.

    Usage:

        >>> api = Api(access_token)
        >>> base = Base(api, "base_id")
        >>> Table(base, "table_name")

    Can also be accessed as:

        >>> Api(access_token).base("base_id").table("table_name")

    The previous method of constructing Table instances (by directly providing ``api_key`` and ``base_id``)
    has been moved into a classmethod, :meth:`from_ids`. This is provided for convenience to developers
    who may be switching from 1.5 to 2.0.

        >>> Table.from_ids(api_key=access_token, base_id="base_id", table_name="table_name")
    """

    base: "pyairtable.api.base.Base"
    name: str

    def __init__(self, base: "pyairtable.api.base.Base", table_name: str) -> None:
        self.base = base
        self.name = table_name

    def __repr__(self) -> str:
        return f"<Table base_id={self.base.id!r} table_name={self.name!r}>"

    @classmethod
    def from_ids(
        cls, api_key: str, base_id: str, table_name: str, **api_kwargs: Any
    ) -> SelfType:
        api = pyairtable.api.api.Api(api_key, **api_kwargs)
        base = api.base(base_id)
        return cls(base, table_name)

    @property
    def api(self) -> "pyairtable.api.api.Api":
        return self.base.api

    @property
    def url(self) -> str:
        """
        Return the URL for this table.
        """
        return self.api.build_url(self.base.id, urllib.parse.quote(self.name, safe=""))

    def record_url(self, record_id: RecordId) -> str:
        """
        Return the URL for the given record ID.
        """
        return f"{self.url}/{record_id}"

    def get(self, record_id: RecordId, **options: Any) -> RecordDict:
        """
        Retrieves a record by its ID.

        >>> record = api.get('base_id', 'table_name', 'recwPQIfs4wKPyc9D')

        Args:
            record_id: |arg_record_id|

        Keyword Args:
            cell_format: |kwarg_cell_format|
            time_zone: |kwarg_time_zone|
            user_locale: |kwarg_user_locale|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|
        """
        record = self.api.request("get", self.record_url(record_id), options=options)
        return assert_typed_dict(RecordDict, record)

    def iterate(self, **options: Any) -> Iterator[List[RecordDict]]:
        """
        Performs a records request and iterates through each apge of results.
        To get all records at once use :meth:`all`.

        >>> list(api.iterate('base_id', 'table_name'))
        [[{"id": ...}, {"id": ...}, {"id": ...}, ...],
         [{"id": ...}, {"id": ...}, {"id": ...}, ...],
         [{"id": ...}]

        Keyword Args:
            view: |kwarg_view|
            page_size: |kwarg_page_size|
            max_records: |kwarg_max_records|
            fields: |kwarg_fields|
            sort: |kwarg_sort|
            formula: |kwarg_formula|
            cell_format: |kwarg_cell_format|
            user_locale: |kwarg_user_locale|
            time_zone: |kwarg_time_zone|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|
        """
        offset = None
        while True:
            if offset:
                options.update({"offset": offset})
            data = self.api.request(
                method="get",
                url=self.url,
                fallback=("post", f"{self.url}/listRecords"),
                options=options,
            )
            records = assert_typed_dicts(RecordDict, data.get("records", []))
            yield records
            offset = data.get("offset")
            if not offset:
                break
            self.api.wait()

    def first(self, **options: Any) -> Optional[RecordDict]:
        """
        Retrieves the first matching record.
        Returns ``None`` if no records are returned.

        This is similar to :meth:`~pyairtable.api.Table.all`, except
        it sets ``page_size`` and ``max_records`` to ``1``.

        Keyword Args:
            view: |kwarg_view|
            fields: |kwarg_fields|
            sort: |kwarg_sort|
            formula: |kwarg_formula|
            cell_format: |kwarg_cell_format|
            user_locale: |kwarg_user_locale|
            time_zone: |kwarg_time_zone|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|
        """
        options.update(dict(page_size=1, max_records=1))
        for page in self.iterate(**options):
            for record in page:
                return record
        return None

    def all(self, **options: Any) -> List[RecordDict]:
        """
        Retrieves all matching records in a single list.

        >>> api.all('base_id', 'table_name', view='MyView', fields=['ColA', '-ColB'])
        [{'fields': ...}, ...]
        >>> api.all('base_id', 'table_name', max_records=50)
        [{'fields': ...}, ...]

        Keyword Args:
            view: |kwarg_view|
            page_size: |kwarg_page_size|
            max_records: |kwarg_max_records|
            fields: |kwarg_fields|
            sort: |kwarg_sort|
            formula: |kwarg_formula|
            cell_format: |kwarg_cell_format|
            user_locale: |kwarg_user_locale|
            time_zone: |kwarg_time_zone|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|
        """
        return [record for page in self.iterate(**options) for record in page]

    def create(
        self,
        fields: Fields,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> RecordDict:
        """
        Creates a new record

        >>> record = {'Name': 'John'}
        >>> api.create('base_id', 'table_name', record)

        Args:
            fields: Fields to insert. Must be a dict with field names or IDs as keys.
            typecast: |kwarg_typecast|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|
        """
        created = self.api.request(
            method="post",
            url=self.url,
            json={
                "fields": fields,
                "typecast": typecast,
                "returnFieldsByFieldId": return_fields_by_field_id,
            },
        )
        return assert_typed_dict(RecordDict, created)

    def batch_create(
        self,
        records: List[Fields],
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> List[RecordDict]:
        """
        Creates a number of new records in batches set by ``MAX_RECORDS_PER_REQUEST``.

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> api.batch_create('base_id', 'table_name', records)

        Args:
            records: List of dicts representing records to be created.
            typecast: |kwarg_typecast|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|
        """
        inserted_records = []

        for chunk in self.api.chunked(records):
            new_records = [{"fields": fields} for fields in chunk]
            response = self.api.request(
                method="post",
                url=self.url,
                json={
                    "records": new_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": return_fields_by_field_id,
                },
            )
            inserted_records += assert_typed_dicts(RecordDict, response["records"])
            self.api.wait()

        return inserted_records

    def update(
        self,
        record_id: RecordId,
        fields: Fields,
        replace: bool = False,
        typecast: bool = False,
    ) -> RecordDict:
        """
        Updates a record by its record id.
        Only Fields passed are updated, the rest are left as is.

        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
        {id: 'recwPQIfs4wKPyc9D', 'fields': {'First Name': 'John', 'Age': 21}}
        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 22}, replace=True)
        {id: 'recwPQIfs4wKPyc9D', 'fields': {'Age': 22}}

        Args:
            record_id: |arg_record_id|
            fields: Fields to update. Must be a dict with column names or IDs as keys.
            replace: |kwarg_replace|
            typecast: |kwarg_typecast|
        """
        method = "put" if replace else "patch"
        updated = self.api.request(
            method=method,
            url=self.record_url(record_id),
            json={"fields": fields, "typecast": typecast},
        )
        return assert_typed_dict(RecordDict, updated)

    def batch_update(
        self,
        records: List[UpdateRecordDict],
        replace: bool = False,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> List[RecordDict]:
        """
        Updates a records by their record id's in batch.

        Args:
            records: Records to update.
            replace: |kwarg_replace|
            typecast: |kwarg_typecast|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            The list of updated records.
        """
        updated_records = []
        method = "put" if replace else "patch"

        for chunk in self.api.chunked(records):
            chunk_records = [{"id": x["id"], "fields": x["fields"]} for x in chunk]
            response = self.api.request(
                method=method,
                url=self.url,
                json={
                    "records": chunk_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": return_fields_by_field_id,
                },
            )
            updated_records += assert_typed_dicts(RecordDict, response["records"])
            self.api.wait()

        return updated_records

    def batch_upsert(
        self,
        records: List[UpdateRecordDict],
        key_fields: List[FieldName],
        replace: bool = False,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> List[RecordDict]:
        """
        Updates or creates records in batches, either using ``id`` (if given) or using a set of
        fields (``key_fields``) to look for matches. For more information on how this operation
        behaves, see Airtable's API documentation for `Update multiple records <https://airtable.com/developers/web/api/update-multiple-records#request-performupsert-fieldstomergeon>`__.

        .. versionadded:: 1.5.0

        Args:
            records: Records to update.
            key_fields: List of field names that Airtable should use to match
                records in the input with existing records on the server.
            replace: |kwarg_replace|
            typecast: |kwarg_typecast|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            The list of updated records.
        """
        # The API will reject a request where a record is missing any of fieldsToMergeOn,
        # but we might not reach that error until we've done several batch operations.
        # To spare implementers from having to recover from a partially applied upsert,
        # and to simplify our API, we will raise an exception before any network calls.
        for record in records:
            if "id" in record:
                continue
            missing = set(key_fields) - set(record.get("fields", []))
            if missing:
                raise ValueError(f"missing {missing!r} in {record['fields'].keys()!r}")

        updated_records = []
        method = "put" if replace else "patch"
        for chunk in self.api.chunked(records):
            formatted_records = [
                {k: v for (k, v) in record.items() if k in ("id", "fields")}
                for record in chunk
            ]
            response = self.api.request(
                method=method,
                url=self.url,
                json={
                    "records": formatted_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": return_fields_by_field_id,
                    "performUpsert": {"fieldsToMergeOn": key_fields},
                },
            )
            updated_records += assert_typed_dicts(RecordDict, response["records"])
            self.api.wait()

        return updated_records

    def delete(self, record_id: RecordId) -> RecordDeletedDict:
        """
        Deletes a record by its id

        >>> record = api.match('base_id', 'table_name', 'Employee Id', 'DD13332454')
        >>> api.delete('base_id', 'table_name', record['id'])

        Args:
            record_id: |arg_record_id|

        Returns:
            A dict containing the ID of the deleted record.
        """
        return assert_typed_dict(
            RecordDeletedDict,
            self.api.request("delete", self.record_url(record_id)),
        )

    def batch_delete(self, record_ids: List[RecordId]) -> List[RecordDeletedDict]:
        """
        Breaks records into batches of 10 and deletes in batches, following set
        API Rate Limit (5/sec).
        To change the rate limit set value of ``API_LIMIT`` to
        the time in seconds it should sleep before calling the function again.

        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> api.batch_delete('base_id', 'table_name', records_ids)

        Args:
            record_ids: Record IDs to delete

        Returns:
            List of dicts containing IDs of the deleted records.
        """
        deleted_records = []

        for chunk in self.api.chunked(record_ids):
            result = self.api.request("delete", self.url, params={"records[]": chunk})
            deleted_records += assert_typed_dicts(RecordDeletedDict, result["records"])
            self.api.wait()

        return deleted_records
