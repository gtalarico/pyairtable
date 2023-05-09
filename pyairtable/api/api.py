from typing import List, Optional

from .abstract import ApiAbstract, TimeoutTuple
from .retrying import Retry


class Api(ApiAbstract):
    """
    Represents an Airtable Api.

    The Api Key or Authorization Token is provided on init and ``base_id`` and ``table_id``
    can be provided on each method call.

    If you are only operating on one Table, or one Base, consider using
    :class:`Base` or :class:`Table`.

    Usage:
        >>> api = Api('auth_token')
        >>> api.all('base_id', 'table_name')
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout: Optional[TimeoutTuple] = None,
        retry_strategy: Optional[Retry] = None,
        endpoint_url: str = "https://api.airtable.com",
    ):
        """

        Args:
            api_key: |arg_api_key|

        Keyword Args:
            timeout (``Tuple``): |arg_timeout|
            retry_strategy (``Retry``): |arg_retry_strategy|
            endpoint_url (``str``): |arg_endpoint_url|
        """
        super().__init__(
            api_key,
            timeout=timeout,
            retry_strategy=retry_strategy,
            endpoint_url=endpoint_url,
        )

    def get_table(self, base_id: str, table_name: str) -> "Table":
        """
        Returns a new :class:`Table` instance using all shared
        attributes from :class:`Api`
        """
        return Table(
            self.api_key,
            base_id,
            table_name,
            timeout=self.timeout,
            endpoint_url=self.endpoint_url,
        )

    def get_base(self, base_id: str) -> "Base":
        """
        Returns a new :class:`Base` instance using all shared
        attributes from :class:`Api`
        """
        return Base(
            self.api_key, base_id, timeout=self.timeout, endpoint_url=self.endpoint_url
        )

    def get_record_url(self, base_id: str, table_name: str, record_id: str):
        """
        Returns a url for the provided record

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|

        """
        return super()._get_record_url(base_id, table_name, record_id)

    def get(self, base_id: str, table_name: str, record_id: str, **options):
        """
        Retrieves a record by its id

        >>> record = api.get('base_id', 'table_name', 'recwPQIfs4wKPyc9D')

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            record_id: |arg_record_id|

        Keyword Args:
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            record: Record
        """
        return super()._get_record(base_id, table_name, record_id, **options)

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
            cell_format: |kwarg_cell_format|
            user_locale: |kwarg_user_locale|
            time_zone: |kwarg_time_zone|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

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
        it sets ``page_size`` and ``max_records`` to ``1``.

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|

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
        return super()._first(base_id, table_name, **options)

    def all(self, base_id: str, table_name: str, **options):
        """
        Retrieves all records repetitively and returns a single list.

        >>> api.all('base_id', 'table_name', view='MyView', fields=['ColA', '-ColB'])
        [{'fields': ... }, ...]
        >>> api.all('base_id', 'table_name', max_records=50)
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
            cell_format: |kwarg_cell_format|
            user_locale: |kwarg_user_locale|
            time_zone: |kwarg_time_zone|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            records (``list``): List of Records

        >>> records = all(max_records=3, view='All')

        """
        return super()._all(base_id, table_name, **options)

    def create(
        self,
        base_id: str,
        table_name: str,
        fields: dict,
        typecast=False,
        return_fields_by_field_id=False,
    ):
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
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            record (``dict``): Inserted record

        """
        return super()._create(
            base_id,
            table_name,
            fields,
            typecast=typecast,
            return_fields_by_field_id=return_fields_by_field_id,
        )

    def batch_create(
        self,
        base_id: str,
        table_name: str,
        records,
        typecast=False,
        return_fields_by_field_id=False,
    ):
        """
        Breaks records into chunks of 10 and inserts them in batches.
        Follows the set API rate.
        To change the rate limit you can change ``API_LIMIT = 0.2``
        (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> api.batch_create('base_id', 'table_name', records)

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            records(``List[dict]``): List of dictionaries representing
                records to be created.

        Keyword Args:
            typecast: |kwarg_typecast|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            records (``list``): list of added records
        """
        return super()._batch_create(
            base_id,
            table_name,
            records,
            typecast=typecast,
            return_fields_by_field_id=return_fields_by_field_id,
        )

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
                Must be a dict with column names or IDs as keys

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
        return_fields_by_field_id=False,
    ):
        """
        Updates a records by their record id's in batch.

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            records(``list``): List of dict: [{"id": record_id, "fields": fields_to_update_dict}]

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            typecast: |kwarg_typecast|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            records(``list``): list of updated records
        """
        return super()._batch_update(
            base_id,
            table_name,
            records,
            replace=replace,
            typecast=typecast,
            return_fields_by_field_id=return_fields_by_field_id,
        )

    def batch_upsert(
        self,
        base_id: str,
        table_name: str,
        records: List[dict],
        key_fields: List[str],
        replace=False,
        typecast=False,
        return_fields_by_field_id=False,
    ):
        """
        Updates or creates records in batches, either using ``id`` (if given) or using a set of
        fields (``key_fields``) to look for matches. For more information on how this operation
        behaves, see Airtable's API documentation for `Update multiple records <https://airtable.com/developers/web/api/update-multiple-records#request-performupsert-fieldstomergeon>`_.

        .. versionadded:: 1.5.0

        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
            records (``list``): List of dict: [{"id": record_id, "fields": fields_to_update_dict}]
            key_fields (``list``): List of field names that Airtable should use to match
                records in the input with existing records on the server.

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - e.g. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            typecast: |kwarg_typecast|
            return_fields_by_field_id: |kwarg_return_fields_by_field_id|

        Returns:
            records (``list``): list of updated records
        """
        return super()._batch_upsert(
            base_id=base_id,
            table_name=table_name,
            records=records,
            key_fields=key_fields,
            replace=replace,
            typecast=typecast,
            return_fields_by_field_id=return_fields_by_field_id,
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
        return "<pyairtable.Api>"


from pyairtable.api.base import Base  # noqa
from pyairtable.api.table import Table  # noqa
