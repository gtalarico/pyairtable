from typing import List
from .api import ApiBase


class Table(ApiBase):
    """
    Represents an Airtable Table. This calss is similar to :class:`~pyairtable.api.Api`,
    except ``base_id`` and ``table_id`` are provided on init instead of provided
    on each method call.

    Usage:
        >>> table = Table('apikey', 'base_id', 'table_name')
        >>> table.all()
    """

    base_id: str
    table_name: str

    def __init__(self, api_key: str, base_id: str, table_name: str, *, timeout=None):
        """
        Args:
            api_key: |arg_api_key|
            base_id: |arg_base_id|
            table_name: |arg_table_name|

        Keyword Args:
            timeout(``Tuple``): |arg_timeout|
        """
        self.base_id = base_id
        self.table_name = table_name
        super().__init__(api_key, timeout=timeout)

    @property
    def table_url(self):
        """Returns the table URL"""
        return super().get_table_url(self.base_id, self.table_name)

    def get_record_url(self, record_id: str):
        """
        Same as :meth:`Api.get_record_url <pyairtable.api.Api.get_record_url>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._get_record_url(self.base_id, self.table_name, record_id)

    def get(self, record_id: str):
        """
        Same as :meth:`Api.get <pyairtable.api.Api.get>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._get_record(self.base_id, self.table_name, record_id)

    def iterate(self, **options):
        """
        Same as :meth:`Api.iterate <pyairtable.api.Api.iterate>`
        but without ``base_id`` and ``table_name`` arg.
        """
        gen = super()._iterate(self.base_id, self.table_name, **options)
        for i in gen:
            yield i

    def first(self, **options):
        """
        Same as :meth:`Api.first <pyairtable.api.Api.first>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._first(self.base_id, self.table_name, **options)

    def all(self, **options):
        """
        Same as :meth:`Api.all <pyairtable.api.Api.all>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._all(self.base_id, self.table_name, **options)

    def create(self, fields: dict, typecast=False):
        """
        Same as :meth:`Api.create <pyairtable.api.Api.create>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._create(self.base_id, self.table_name, fields, typecast=typecast)

    def batch_create(self, records, typecast=False):
        """
        Same as :meth:`Api.batch_create <pyairtable.api.Api.batch_create>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._batch_create(
            self.base_id, self.table_name, records, typecast=typecast
        )

    def update(
        self,
        record_id: str,
        fields: dict,
        replace=False,
        typecast=False,
    ):
        """
        Same as :meth:`Api.update <pyairtable.api.Api.update>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._update(
            self.base_id,
            self.table_name,
            record_id,
            fields,
            replace=replace,
            typecast=typecast,
        )

    def batch_update(self, records: List[dict], replace=False, typecast=False):
        """
        Same as :meth:`Api.batch_update <pyairtable.api.Api.batch_update>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._batch_update(
            self.base_id, self.table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, record_id: str):
        """
        Same as :meth:`Api.delete <pyairtable.api.Api.delete>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._delete(self.base_id, self.table_name, record_id)

    def batch_delete(self, record_ids: List[str]):
        """
        Same as :meth:`Api.batch_delete <pyairtable.api.Api.batch_delete>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._batch_delete(self.base_id, self.table_name, record_ids)

    def __repr__(self) -> str:
        return "<Table base_id={} table_name={}>".format(self.base_id, self.table_name)
