from typing import List

from .api import ApiBase


class Base(ApiBase):
    """
    Represents an Airtable Base. This calss is similar to :class:`~airtable.api.Api`,
    except ``base_id`` is provided on init instead of provided on each method call.

    Usage:
        >>> base = Base('apikey', 'base_id')
        >>> base.all()
    """

    base_id: str

    def __init__(self, api_key: str, base_id: str, timeout=None):
        """
        Args:
            api_key: |arg_api_key|
            base_id: |arg_base_id|

        Keyword Args:
            timeout(``Tuple``): |arg_timeout|
        """
        self.base_id = base_id
        super().__init__(api_key, timeout=timeout)

    def get_record_url(self, table_name: str, record_id: str):
        """
        Same as :meth:`Api.get_record_url <airtable.api.Api.get_record_url>`
        but without ``base_id`` arg.
        """
        return super()._get_record_url(self.base_id, table_name, record_id)

    def get(self, table_name: str, record_id: str):
        """
        Same as :meth:`Api.get <airtable.api.Api.get>`
        but without ``base_id`` arg.
        """
        return super()._get_record(self.base_id, table_name, record_id)

    def iterate(self, table_name: str, **options):
        """
        Same as :meth:`Api.iterate <airtable.api.Api.iterate>`
        but without ``base_id`` arg.
        """
        gen = super()._iterate(self.base_id, table_name, **options)
        for i in gen:
            yield i

    def first(self, table_name: str, **options):
        """
        Same as :meth:`Api.first <airtable.api.Api.first>`
        but without ``base_id`` arg.
        """
        return super()._first(self.base_id, table_name, **options)

    def all(self, table_name: str, **options):
        """
        Same as :meth:`Api.all <airtable.api.Api.all>`
        but without ``base_id`` arg.
        """
        return super()._all(self.base_id, table_name, **options)

    def create(self, table_name: str, fields: dict, typecast=False):
        """
        Same as :meth:`Api.create <airtable.api.Api.create>`
        but without ``base_id`` arg.
        """
        return super()._create(self.base_id, table_name, fields, typecast=typecast)

    def batch_create(self, table_name: str, records, typecast=False):
        """
        Same as :meth:`Api.batch_create <airtable.api.Api.batch_create>`
        but without ``base_id`` arg.
        """
        return super()._batch_create(
            self.base_id, table_name, records, typecast=typecast
        )

    def update(
        self,
        table_name: str,
        record_id: str,
        fields: dict,
        replace=False,
        typecast=False,
    ):
        """
        Same as :meth:`Api.update <airtable.api.Api.update>`
        but without ``base_id`` arg.
        """
        return super()._update(
            self.base_id,
            table_name,
            record_id,
            fields,
            replace=replace,
            typecast=typecast,
        )

    def batch_update(
        self, table_name: str, records: List[dict], replace=False, typecast=False
    ):
        """
        Same as :meth:`Api.batch_update <airtable.api.Api.batch_update>`
        but without ``base_id`` arg.
        """
        return super()._batch_update(
            self.base_id, table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, table_name: str, record_id: str):
        """
        Same as :meth:`Api.delete <airtable.api.Api.delete>`
        but without ``base_id`` arg.
        """
        return super()._delete(self.base_id, table_name, record_id)

    def batch_delete(self, table_name: str, record_ids: List[str]):
        """
        Same as :meth:`Api.batch_delete <airtable.api.Api.batch_delete>`
        but without ``base_id`` arg.
        """
        return super()._batch_delete(self.base_id, table_name, record_ids)

    def __repr__(self) -> str:
        return "<Airtable Base id={}>".format(self.base_id)
