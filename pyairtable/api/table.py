import base64
import mimetypes
import os
import urllib.parse
import warnings
from functools import cached_property
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Union,
    overload,
)

import pyairtable.models
from pyairtable.api.types import (
    FieldName,
    RecordDeletedDict,
    RecordDict,
    RecordId,
    UpdateRecordDict,
    UploadAttachmentResultDict,
    UpsertResultDict,
    WritableFields,
    assert_typed_dict,
    assert_typed_dicts,
)
from pyairtable.formulas import Formula, to_formula_str
from pyairtable.models.schema import FieldSchema, TableSchema, parse_field_schema
from pyairtable.utils import Url, UrlBuilder, is_table_id

if TYPE_CHECKING:
    from pyairtable.api.api import Api, TimeoutTuple
    from pyairtable.api.base import Base
    from pyairtable.api.retrying import Retry


class Table:
    """
    Represents an Airtable table.

    Usage:
        >>> api = Api(access_token)
        >>> table = api.table("base_id", "table_name")
        >>> records = table.all()
    """

    #: The base that this table belongs to.
    base: "Base"

    #: Can be either the table name or the table ID (``tblXXXXXXXXXXXXXX``).
    name: str

    # Cached schema information to reduce API calls
    _schema: Optional[TableSchema] = None

    class _urls(UrlBuilder):
        #: URL for retrieving all records in the table
        records = Url("{base.id}/{self.id_or_name}")

        #: URL for retrieving all records in the table via POST,
        #: when the request is too large to fit into GET parameters.
        records_post = records / "listRecords"
        fields = Url("meta/bases/{base.id}/tables/{self.id_or_name}/fields")

        def record(self, record_id: RecordId) -> Url:
            """
            URL for a specific record in the table.
            """
            return self.records / record_id

        def record_comments(self, record_id: RecordId) -> Url:
            """
            URL for comments on a specific record in the table.
            """
            return self.record(record_id) / "comments"

        def upload_attachment(self, record_id: RecordId, field: str) -> Url:
            """
            URL for uploading an attachment to a specific field in a specific record.
            """
            url = self.build_url(f"{{base.id}}/{record_id}/{field}/uploadAttachment")
            return url.replace_url(netloc="content.airtable.com")

    urls = cached_property(_urls)

    @overload
    def __init__(
        self,
        api_key: str,
        base_id: str,
        table_name: str,
        *,
        timeout: Optional["TimeoutTuple"] = None,
        retry_strategy: Optional["Retry"] = None,
        endpoint_url: str = "https://api.airtable.com",
    ): ...

    @overload
    def __init__(
        self,
        api_key: None,
        base_id: "Base",
        table_name: str,
    ): ...

    @overload
    def __init__(
        self,
        api_key: None,
        base_id: "Base",
        table_name: TableSchema,
    ): ...

    def __init__(
        self,
        api_key: Union[None, str],
        base_id: Union["Base", str],
        table_name: Union[str, TableSchema],
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
            self.base = api.base(base_id)
        elif api_key is None and isinstance(base := base_id, pyairtable.api.base.Base):
            self.base = base
        else:
            raise TypeError(
                "Table() expects (None, Base, str | TableSchema);"
                f" got ({type(api_key)}, {type(base_id)}, {type(table_name)})"
            )

        if isinstance(table_name, str):
            self.name = table_name
        elif isinstance(schema := table_name, TableSchema):
            self._schema = schema
            self.name = schema.name
        else:
            raise TypeError(
                "Table() expects (None, Base, str | TableSchema);"
                f" got ({type(api_key)}, {type(base_id)}, {type(table_name)})"
            )

    def __repr__(self) -> str:
        if self._schema:
            return f"<Table base={self.base.id!r} id={self._schema.id!r} name={self._schema.name!r}>"
        return f"<Table base={self.base.id!r} name={self.name!r}>"

    @property
    def id(self) -> str:
        """
        Get the table's Airtable ID.

        If the instance was created with a name rather than an ID, this property will perform
        an API request to retrieve the base's schema. For example:

        .. code-block:: python

            # This will not create any network traffic
            >>> table = base.table('tbl00000000000123')
            >>> table.id
            'tbl00000000000123'

            # This will fetch schema for the base when `table.id` is called
            >>> table = base.table('Table Name')
            >>> table.id
            'tbl00000000000123'
        """
        if is_table_id(self.name):
            return self.name
        return self.schema().id

    @property
    def id_or_name(self, quoted: bool = True) -> str:
        """
        Return the table ID if it is known, otherwise the table name used for the constructor.
        This is the URL component used to identify the table in Airtable's API.

        Args:
            quoted: Whether to return a URL-encoded value.

        Usage:

            >>> table = base.table("Apartments")
            >>> table.id_or_name
            'Apartments'
            >>> table.schema()
            >>> table.id_or_name
            'tblXXXXXXXXXXXXXX'
        """
        value = self._schema.id if self._schema else self.name
        value = value if not quoted else urllib.parse.quote(value, safe="")
        return value

    @property
    def api(self) -> "Api":
        """
        The API connection used by the table's :class:`~pyairtable.Base`.
        """
        return self.base.api

    def get(self, record_id: RecordId, **options: Any) -> RecordDict:
        """
        Retrieve a record by its ID.

        >>> table.get('recwPQIfs4wKPyc9D')
        {'id': 'recwPQIfs4wKPyc9D', 'fields': {'First Name': 'John', 'Age': 21}}

        Args:
            record_id: |arg_record_id|

        Keyword Args:
            cell_format: |kwarg_cell_format|
            time_zone: |kwarg_time_zone|
            user_locale: |kwarg_user_locale|
            use_field_ids: |kwarg_use_field_ids|
        """
        if self.api.use_field_ids:
            options.setdefault("use_field_ids", self.api.use_field_ids)
        record = self.api.get(self.urls.record(record_id), options=options)
        return assert_typed_dict(RecordDict, record)

    def iterate(self, **options: Any) -> Iterator[List[RecordDict]]:
        """
        Iterate through each page of results from `List records <https://airtable.com/developers/web/api/list-records>`_.
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
            use_field_ids: |kwarg_use_field_ids|
        """
        if isinstance(formula := options.get("formula"), Formula):
            options["formula"] = to_formula_str(formula)
        if self.api.use_field_ids:
            options.setdefault("use_field_ids", self.api.use_field_ids)
        for page in self.api.iterate_requests(
            method="get",
            url=self.urls.records,
            fallback=("post", self.urls.records_post),
            options=options,
        ):
            yield assert_typed_dicts(RecordDict, page.get("records", []))

    def all(self, **options: Any) -> List[RecordDict]:
        """
        Retrieve all matching records in a single list.

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
            use_field_ids: |kwarg_use_field_ids|
        """
        return [record for page in self.iterate(**options) for record in page]

    def first(self, **options: Any) -> Optional[RecordDict]:
        """
        Retrieve the first matching record.
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
            use_field_ids: |kwarg_use_field_ids|
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
        use_field_ids: Optional[bool] = None,
    ) -> RecordDict:
        """
        Create a new record

        >>> record = {'Name': 'John'}
        >>> table = api.table('base_id', 'table_name')
        >>> table.create(record)

        Args:
            fields: Fields to insert. Must be a dict with field names or IDs as keys.
            typecast: |kwarg_typecast|
            use_field_ids: |kwarg_use_field_ids|
        """
        if use_field_ids is None:
            use_field_ids = self.api.use_field_ids
        created = self.api.post(
            url=self.urls.records,
            json={
                "fields": fields,
                "typecast": typecast,
                "returnFieldsByFieldId": use_field_ids,
            },
        )
        return assert_typed_dict(RecordDict, created)

    def batch_create(
        self,
        records: Iterable[WritableFields],
        typecast: bool = False,
        use_field_ids: Optional[bool] = None,
    ) -> List[RecordDict]:
        """
        Create a number of new records in batches.

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
            records: Iterable of dicts representing records to be created.
            typecast: |kwarg_typecast|
            use_field_ids: |kwarg_use_field_ids|
        """
        inserted_records = []
        if use_field_ids is None:
            use_field_ids = self.api.use_field_ids

        # If we got an iterator, exhaust it and collect it into a list.
        records = list(records)

        for chunk in self.api.chunked(records):
            new_records = [{"fields": fields} for fields in chunk]
            response = self.api.post(
                url=self.urls.records,
                json={
                    "records": new_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": use_field_ids,
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
        use_field_ids: Optional[bool] = None,
    ) -> RecordDict:
        """
        Update a particular record ID with the given fields.

        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
        {'id': 'recwPQIfs4wKPyc9D', 'fields': {'First Name': 'John', 'Age': 21}}
        >>> table.update('recwPQIfs4wKPyc9D', {"Age": 22}, replace=True)
        {'id': 'recwPQIfs4wKPyc9D', 'fields': {'Age': 22}}

        Args:
            record_id: |arg_record_id|
            fields: Fields to update. Must be a dict with column names or IDs as keys.
            replace: |kwarg_replace|
            typecast: |kwarg_typecast|
            use_field_ids: |kwarg_use_field_ids|
        """
        if use_field_ids is None:
            use_field_ids = self.api.use_field_ids
        method = "put" if replace else "patch"
        updated = self.api.request(
            method=method,
            url=self.urls.record(record_id),
            json={
                "fields": fields,
                "typecast": typecast,
                "returnFieldsByFieldId": use_field_ids,
            },
        )
        return assert_typed_dict(RecordDict, updated)

    def batch_update(
        self,
        records: Iterable[UpdateRecordDict],
        replace: bool = False,
        typecast: bool = False,
        use_field_ids: Optional[bool] = None,
    ) -> List[RecordDict]:
        """
        Update several records in batches.

        Args:
            records: Records to update.
            replace: |kwarg_replace|
            typecast: |kwarg_typecast|
            use_field_ids: |kwarg_use_field_ids|

        Returns:
            The list of updated records.
        """
        updated_records = []
        method = "put" if replace else "patch"
        if use_field_ids is None:
            use_field_ids = self.api.use_field_ids

        # If we got an iterator, exhaust it and collect it into a list.
        records = list(records)

        for chunk in self.api.chunked(records):
            chunk_records = [{"id": x["id"], "fields": x["fields"]} for x in chunk]
            response = self.api.request(
                method=method,
                url=self.urls.records,
                json={
                    "records": chunk_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": use_field_ids,
                },
            )
            updated_records += assert_typed_dicts(RecordDict, response["records"])

        return updated_records

    def batch_upsert(
        self,
        records: Iterable[Dict[str, Any]],
        key_fields: List[FieldName],
        replace: bool = False,
        typecast: bool = False,
        use_field_ids: Optional[bool] = None,
    ) -> UpsertResultDict:
        """
        Update or create records in batches, either using ``id`` (if given) or using a set of
        fields (``key_fields``) to look for matches. For more information on how this operation
        behaves, see Airtable's API documentation for `Update multiple records <https://airtable.com/developers/web/api/update-multiple-records#request-performupsert-fieldstomergeon>`__.

        .. versionadded:: 1.5.0

        Args:
            records: Records to update.
            key_fields: List of field names that Airtable should use to match
                records in the input with existing records on the server.
            replace: |kwarg_replace|
            typecast: |kwarg_typecast|
            use_field_ids: |kwarg_use_field_ids|

        Returns:
            Lists of created/updated record IDs, along with the list of all records affected.
        """
        if use_field_ids is None:
            use_field_ids = self.api.use_field_ids

        # If we got an iterator, exhaust it and collect it into a list.
        records = list(records)

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
                url=self.urls.records,
                json={
                    "records": formatted_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": use_field_ids,
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
        Delete the given record.

        >>> table.delete('recwPQIfs4wKPyc9D')
        {'id': 'recwPQIfs4wKPyc9D', 'deleted': True}

        Args:
            record_id: |arg_record_id|

        Returns:
            Confirmation that the record was deleted.
        """
        return assert_typed_dict(
            RecordDeletedDict,
            self.api.delete(self.urls.record(record_id)),
        )

    def batch_delete(self, record_ids: Iterable[RecordId]) -> List[RecordDeletedDict]:
        """
        Delete the given records, operating in batches.

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

        # If we got an iterator, exhaust it and collect it into a list.
        record_ids = list(record_ids)

        for chunk in self.api.chunked(record_ids):
            result = self.api.delete(self.urls.records, params={"records[]": chunk})
            deleted_records += assert_typed_dicts(RecordDeletedDict, result["records"])

        return deleted_records

    def comments(self, record_id: RecordId) -> List["pyairtable.models.Comment"]:
        """
        Retrieve all comments on the given record.

        Usage:
            >>> table = Api.table("appNxslc6jG0XedVM", "tblslc6jG0XedVMNx")
            >>> table.comments("recMNxslc6jG0XedV")
            [
                Comment(
                    id='comdVMNxslc6jG0Xe',
                    text='Hello, @[usrVMNxslc6jG0Xed]!',
                    created_time=datetime.datetime(...),
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
        url = self.urls.record_comments(record_id)
        ctx = {"record_url": self.urls.record(record_id)}
        return [
            pyairtable.models.Comment.from_api(comment, self.api, context=ctx)
            for page in self.api.iterate_requests("GET", url)
            for comment in page["comments"]
        ]

    def add_comment(
        self,
        record_id: RecordId,
        text: str,
    ) -> "pyairtable.models.Comment":
        """
        Create a comment on a record.
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
        url = self.urls.record_comments(record_id)
        response = self.api.post(url, json={"text": text})
        return pyairtable.models.Comment.from_api(
            response, self.api, context={"record_url": self.urls.record(record_id)}
        )

    def schema(self, *, force: bool = False) -> TableSchema:
        """
        Retrieve the schema of the current table.

        Usage:
            >>> table.schema()
            TableSchema(
                id='tblslc6jG0XedVMNx',
                name='My Table',
                primary_field_id='fld6jG0XedVMNxFQW',
                fields=[...],
                views=[...]
            )

        Args:
            force: |kwarg_force_metadata|
        """
        if force or not self._schema:
            self._schema = self.base.schema(force=force).table(self.name)
        return self._schema

    def create_field(
        self,
        name: str,
        field_type: str,
        description: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> FieldSchema:
        """
        Create a field on the table.

        Usage:
            >>> table.create_field("Attachments", "multipleAttachment")
            FieldSchema(
                id='fldslc6jG0XedVMNx',
                name='Attachments',
                type='multipleAttachment',
                description=None,
                options=MultipleAttachmentsFieldOptions(is_reversed=False)
            )

        Args:
            name: The unique name of the field.
            field_type: One of the `Airtable field types <https://airtable.com/developers/web/api/model/field-type>`__.
            description: A long form description of the table.
            options: Only available for some field types. For more information, read about the
                `Airtable field model <https://airtable.com/developers/web/api/field-model>`__.
        """
        request: Dict[str, Any] = {"name": name, "type": field_type}
        if description:
            request["description"] = description
        if options:
            request["options"] = options
        response = self.api.post(self.urls.fields, json=request)
        # This hopscotch ensures that the FieldSchema object we return has an API and a URL,
        # and that developers don't need to reload our schema to be able to access it.
        field_schema = parse_field_schema(response)
        field_schema._set_api(
            self.api,
            context={
                "base": self.base,
                "table_schema": self._schema or self,
            },
        )
        if self._schema:
            self._schema.fields.append(field_schema)
        return field_schema

    def upload_attachment(
        self,
        record_id: RecordId,
        field: str,
        filename: Union[str, Path],
        content: Optional[Union[str, bytes]] = None,
        content_type: Optional[str] = None,
    ) -> UploadAttachmentResultDict:
        """
        Upload an attachment to the Airtable API, either by supplying the path to the file
        or by providing the content directly as a variable.

        See `Upload attachment <https://airtable.com/developers/web/api/upload-attachment>`__.

        Usage:
            >>> table.upload_attachment("recAdw9EjV90xbZ", "Attachments", "/tmp/example.jpg")
            {
                'id': 'recAdw9EjV90xbZ',
                'createdTime': '2023-05-22T21:24:15.333134Z',
                'fields': {
                    'Attachments': [
                        {
                            'id': 'attW8eG2x0ew1Af',
                            'url': 'https://content.airtable.com/...',
                            'filename': 'example.jpg'
                        }
                    ]
                }
            }

        Args:
            record_id: |arg_record_id|
            field: The ID or name of the ``multipleAttachments`` type field.
            filename: The path to the file to upload. If ``content`` is provided, this
                argument is still used to tell Airtable what name to give the file.
            content: The content of the file as a string or bytes object. If no value
                is provided, pyAirtable will attempt to read the contents of ``filename``.
            content_type: The MIME type of the file. If not provided, the library will attempt to
                guess the content type based on ``filename``.

        Returns:
            A full list of attachments in the given field, including the new attachment.
        """
        if content is None:
            with open(filename, "rb") as fp:
                content = fp.read()
            return self.upload_attachment(
                record_id, field, filename, content, content_type
            )

        filename = os.path.basename(filename)
        if content_type is None:
            if not (content_type := mimetypes.guess_type(filename)[0]):
                warnings.warn(f"Could not guess content-type for {filename!r}")
                content_type = "application/octet-stream"

        # TODO: figure out how to handle the atypical subdomain in a more graceful fashion
        url = self.urls.upload_attachment(record_id, field)
        content = content.encode() if isinstance(content, str) else content
        payload = {
            "contentType": content_type,
            "filename": filename,
            "file": base64.encodebytes(content).decode("utf8"),  # API needs Unicode
        }
        response = self.api.post(url, json=payload)
        return assert_typed_dict(UploadAttachmentResultDict, response)
