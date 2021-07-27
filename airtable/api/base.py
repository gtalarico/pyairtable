"""
The :class:`~airtable.api.Base` class is similar to :class:`~airtable.api.Table`, the main difference is that .
`table_name` is not provided during initialization. Instead, it can be
specified on each request.

>>> base = Base('appEioitPbxI72w06', 'apikey')
>>> base.get_all('Contacts)
[{id:'rec123asa23', fields': {'Last Name': 'Alfred', "Age": 84}, ... ]

"""

from typing import List

from .api import AirtableApi


class Base(AirtableApi):
    def __init__(self, base_id: str, api_key: str, timeout=None):
        self.base_id = base_id
        super().__init__(api_key, timeout=timeout)

    def get_record_url(self, table_name: str, record_id: str):
        return super()._get_record_url(self.base_id, table_name, record_id)

    def get(self, table_name: str, record_id: str):
        return super()._get_record(self.base_id, table_name, record_id)

    def iterate(self, table_name: str, **options):
        gen = super()._iterate(self.base_id, table_name, **options)
        for i in gen:
            yield i

    def first(self, table_name: str, **options):
        return super()._first(self.base_id, table_name ** options)

    def get_all(self, table_name: str, **options):
        return super()._get_all(self.base_id, table_name, **options)

    def create(self, table_name: str, fields: dict, typecast=False):
        return super()._create(self.base_id, table_name, fields, typecast=typecast)

    def batch_create(self, table_name: str, records, typecast=False):
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
        return super()._batch_update(
            self.base_id, table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, table_name: str, record_id: str):
        return super()._delete(self.base_id, table_name, record_id)

    def batch_delete(self, table_name: str, record_ids: List[str]):
        return super()._batch_delete(self.base_id, table_name, record_ids)

    def __repr__(self) -> str:
        return "<Airtable Base id={}>".format(self.base_id)