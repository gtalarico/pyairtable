from typing import List
from .api import AirtableApi


class Table(AirtableApi):
    def __init__(self, base_id, table_name, api_key, *, timeout=None):
        self.base_id = base_id
        self.table_name = table_name
        super().__init__(api_key, timeout=timeout)

    def get(self, record_id):
        return super()._get_record(self.base_id, self.table_name, record_id)

    def get_iter(self, **options):
        gen = super()._get_iter(self.base_id, self.table_name, **options)
        for i in gen:
            yield i

    def first(self, **options):
        return super()._first(self.base_id, self.table_name, **options)

    def get_all(self, **options):
        return super()._get_all(self.base_id, self.table_name, **options)

    def create(self, fields, typecast=False):
        return super()._create(self.base_id, self.table_name, fields, typecast=typecast)

    def batch_create(self, records, typecast=False):
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
        return super()._update(
            self.base_id,
            self.table_name,
            record_id,
            fields,
            replace=replace,
            typecast=typecast,
        )

    def batch_update(self, records: List[dict], replace=False, typecast=False):
        return super()._batch_update(
            self.base_id, self.table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, record_id: str):
        return super()._delete(self.base_id, self.table_name, record_id)

    def batch_delete(self, record_ids: List[str]):
        return super()._batch_delete(self.base_id, self.table_name, record_ids)

    def __repr__(self) -> str:
        return "<Table base_id={} table_name={}>".format(self.base_id, self.table_name)
