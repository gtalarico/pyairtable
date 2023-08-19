import posixpath
import urllib.parse
import warnings
from typing import Any, Iterator, List, Optional, Union, overload

import pyairtable.models
from pyairtable.api.retrying import Retry
from pyairtable.api.types import (
    FieldName,
    RecordDeletedDict,
    RecordDict,
    RecordId,
    UpdateRecordDict,
    UpsertResultDict,
    WritableFields,
    assert_typed_dict,
    assert_typed_dicts,
)


class Table:
    """
    Represents an Airtable table.

    Usage:
        >>> api = Api(access_token)
        >>> table = api.table("base_id", "table_name")
        >>> records = table.all()
    """

    #: The base that this table belongs to.
    base: "pyairtable.api.base.Base"

    #: Can be either the table name or the table ID (``tblXXXXXXXXXXXXXX``).
    name: str

    @overload
    def __init__(
        self,
        api_key: str,
        base_id: str,
        table_name: str,
        *,
        timeout: Optional["pyairtable.api.api.TimeoutTuple"] = None,
        retry_strategy: Optional[Retry] = None,
        endpoint_url: str = "https://api.airtable.com",
    ):
        ...

    @overload
    def __init__(
        self,
        api_key: None,
        base_id: "pyairtable.api.base.Base",
        table_name: str,
    ):
        ...

    def __init__(
        self,
        api_key: Union[None, str],
        base_id: Union["pyairtable.api.base.Base", str],
        table_name: str,
        **kwargs: Any,
    ):
        """
        Old style constructor takes ``str`` arguments, and will create its own
        instance of :class:`Api`. This constructor can also be provided with
        keyword arguments to the :class:`Api` class.

        This approach is deprecated, and will likely be removed in the future.

            >>> Table("api_key", "base_id", "table_name", timeout=(1, 1))

        New style constructor has an odd signature to preserve backwards-compatibility
        with the old style (above), requiring ``None`` as the first argument, followed by
        an instance of :class:`Base`, followed by the table name.

            >>> Table(None, base, "table_name")

        These signatures may change in the future. Developers using this library are
        encouraged to not construct Table instances directly, and instead fetch tables
        via :meth:`Api.table() <pyairtable.Api.table>`.
        """
        if isinstance(api_key, str) and isinstance(base_id, str):
            warnings.warn(
                "Passing API keys or base IDs to pyairtable.Table is deprecated;"
                " use Api.table() or Base.table() instead."
                " See https://pyairtable.rtfd.org/en/latest/migrations.html for details.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            api = pyairtable.api.api.Api(api_key, **kwargs)
            base = api.base(base_id)
        elif api_key is None and isinstance(base_id, pyairtable.api.base.Base):
            base = base_id
        else:
            raise TypeError(
                "Table() expects either (str, str, str) or (None, Base, str);"
                f" got ({type(api_key)}, {type(base_id)}, {type(table_name)})"
            )

        self.base = base
        self.name = table_name

    def __repr__(self) -> str:
        return f"<Table base_id={self.base.id!r} table_name={self.name!r}>"

    @property
    def url(self) -> str:
        """
        Returns the URL for this table.
        """
        return self.api.build_url(self.base.id, urllib.parse.quote(self.name, safe=""))

    def record_url(self, record_id: RecordId, *components: str) -> str:
        """
        Returns the URL for the given record ID, with optional trailing components.
        """
        return posixpath.join(self.url, record_id, *components)

    @property
    def api(self) -> "pyairtable.api.api.Api":
        """
        Returns the same API connection as table's :class:`~pyairtable.Base`.
        """
        return self.base.api

    def get(self, record_id: RecordId, **options: Any) -> RecordDict:
        """
        Retrieves a record by its ID.

        >>> table.get('recwPQIfs4wKPyc9D')
        {'id': 'recwPQIfs4wKPyc9D', 'fields': {'First Name': 'John', 'Age': 21}}

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
        Iterates through each page of results from `List records <https://airtable.com/developers/web/api/list-records>`_.
        To get all records at once, use :meth:`all`.

        >>> it = table.iterate()
        >>> next(it)
        [{"id": ...}, {"id": ...}, {"id": ...}, ...]
        >>> next(it)
        [{"id": ...}, {"id": ...}, {"id": ...}, ...]
        >>> next(it)
        [{"id": ...}]
        >>> next(it)
        Traceback (most recent call last):
        StopIteration

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
        for page in self.api.iterate_requests(
            method="get",
            url=self.url,
            fallback=("post", f"{self.url}/listRecords"),
            options=options,
        ):
            yield assert_typed_dicts(RecordDict, page.get("records", []))

    def all(self, **options: Any) -> List[RecordDict]:
        """
        Retrieves all matching records in a single list.

        >>> table = api.table('base_id', 'table_name')
        >>> table.all(view='MyView', fields=['ColA', '-ColB'])
        [{'fields': ...}, ...]
        >>> table.all(max_records=50)
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

    def first(self, **options: Any) -> Optional[RecordDict]:
        """
        Retrieves the first matching record.
        Returns ``None`` if no records are returned.

        This is similar to :meth:`~pyairtable.Table.all`, except
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

    def create(
        self,
        fields: WritableFields,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> RecordDict:
        """
        Creates a new record

        >>> record = {'Name': 'John'}
        >>> table = api.table('base_id', 'table_name')
        >>> table.create(record)

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
        records: List[WritableFields],
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> List[RecordDict]:
        """
        Creats a number of new records in batches.

        >>> table.batch_create([{'Name': 'John'}, {'Name': 'Marc'}])
        [
            {
                'id': 'recW9e0c9w0er9gug',
                'createdTime': '2017-03-14T22:04:31.000Z',
                'fields': {'Name': 'John'}
            },
            {
                'id': 'recW9e0c9w0er9guh',
                'createdTime': '2017-03-14T22:04:31.000Z',
                'fields': {'Name': 'Marc'}
            }
        ]

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

        return inserted_records

    def update(
        self,
        record_id: RecordId,
        fields: WritableFields,
        replace: bool = False,
        typecast: bool = False,
    ) -> RecordDict:
        """
        Updates a particular record ID with the given fields.

        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
        {'id': 'recwPQIfs4wKPyc9D', 'fields': {'First Name': 'John', 'Age': 21}}
        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 22}, replace=True)
        {'id': 'recwPQIfs4wKPyc9D', 'fields': {'Age': 22}}

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
        Updates several records in batches.

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

        return updated_records

    def batch_upsert(
        self,
        records: List[UpdateRecordDict],
        key_fields: List[FieldName],
        replace: bool = False,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> UpsertResultDict:
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
            Lists of created/updated record IDs, along with the list of all records affected.
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

        method = "put" if replace else "patch"
        result: UpsertResultDict = {
            "updatedRecords": [],
            "createdRecords": [],
            "records": [],
        }

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
            result["updatedRecords"].extend(response["updatedRecords"])
            result["createdRecords"].extend(response["createdRecords"])
            result["records"].extend(
                assert_typed_dicts(RecordDict, response["records"])
            )

        return result

    def delete(self, record_id: RecordId) -> RecordDeletedDict:
        """
        Deletes the given record.

        >>> table.delete('recwPQIfs4wKPyc9D')
        {'id': 'recwPQIfs4wKPyc9D', 'deleted': True}

        Args:
            record_id: |arg_record_id|

        Returns:
            Confirmation that the record was deleted.
        """
        return assert_typed_dict(
            RecordDeletedDict,
            self.api.request("delete", self.record_url(record_id)),
        )

    def batch_delete(self, record_ids: List[RecordId]) -> List[RecordDeletedDict]:
        """
        Deletes the given records, operating in batches.

        >>> table.batch_delete(['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F'])
        [
            {'id': 'recwPQIfs4wKPyc9D', 'deleted': True},
            {'id': 'recwDxIfs3wDPyc3F', 'deleted': True}
        ]

        Args:
            record_ids: Record IDs to delete

        Returns:
            Confirmation that the records were deleted.
        """
        deleted_records = []

        for chunk in self.api.chunked(record_ids):
            result = self.api.request("delete", self.url, params={"records[]": chunk})
            deleted_records += assert_typed_dicts(RecordDeletedDict, result["records"])

        return deleted_records

    def comments(self, record_id: RecordId) -> List["pyairtable.models.Comment"]:
        """
        Returns a list of comments on the given record.

        Usage:
            >>> table = Api.table("appNxslc6jG0XedVM", "tblslc6jG0XedVMNx")
            >>> table.comments("recMNxslc6jG0XedV")
            [
                Comment(
                    id='comdVMNxslc6jG0Xe',
                    text='Hello, @[usrVMNxslc6jG0Xed]!',
                    created_time='2023-06-07T17:46:24.435891',
                    last_updated_time=None,
                    mentioned={
                        'usrVMNxslc6jG0Xed': Mentioned(
                            display_name='Alice',
                            email='alice@example.com',
                            id='usrVMNxslc6jG0Xed',
                            type='user'
                        )
                    },
                    author=Collaborator(
                        id='usr0000pyairtable',
                        email='pyairtable@example.com',
                        name='Your pyairtable access token'
                    )
                )
            ]

        Args:
            record_id: |arg_record_id|
        """
        url = self.record_url(record_id, "comments")
        return [
            pyairtable.models.Comment.from_api(
                api=self.api,
                url=self.record_url(record_id, "comments", comment["id"]),
                obj=comment,
            )
            for page in self.api.iterate_requests("GET", url)
            for comment in page["comments"]
        ]

    def add_comment(
        self,
        record_id: RecordId,
        text: str,
    ) -> "pyairtable.models.Comment":
        """
        Creates a comment on a record.
        See `Create comment <https://airtable.com/developers/web/api/create-comment>`_ for details.

        Usage:
            >>> table = Api.table("appNxslc6jG0XedVM", "tblslc6jG0XedVMNx")
            >>> comment = table.add_comment("recMNxslc6jG0XedV", "Hello, @[usrVMNxslc6jG0Xed]!")
            >>> comment.text = "Never mind!"
            >>> comment.save()
            >>> comment.delete()

        Args:
            record_id: |arg_record_id|
            text: The text of the comment. Use ``@[usrIdentifier]`` to mention users.
        """
        url = self.record_url(record_id, "comments")
        response = self.api.request("POST", url, json={"text": text})
        return pyairtable.models.Comment.from_api(
            api=self.api,
            url=self.record_url(record_id, "comments", response["id"]),
            obj=response,
        )


# These are at the bottom of the module to avoid circular imports
import pyairtable.api.api  # noqa
import pyairtable.api.base  # noqa
