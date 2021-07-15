from typing import List
from .base import Base


class Table(Base):
    def __init__(self, base_id, table_name, api_key, timeout=None):
        self.table_name = table_name
        super().__init__(base_id, api_key, timeout=None)

    def get(self, record_id):
        return super().get(self.table_name, record_id)

    def get_iter(self, **options):
        return super().get_iter(self.table_name, **options)

    def get_all(self, **options):
        all_records = []
        for records in super().get_iter(self.table_name, **options):
            all_records.extend(records)
        return all_records

    def create(self, fields, typecast=False):
        return super().create(self.table_name, fields, typecast=typecast)

    def batch_create(self, records, typecast=False):
        return super().batch_create(self.table_name, records, typecast=typecast)

    def update(
        self,
        record_id: str,
        fields: dict,
        replace=False,
        typecast=False,
    ):
        return super().update(
            self.table_name, record_id, fields, replace=replace, typecast=typecast
        )

    def batch_update(self, records: List[dict], replace=False, typecast=False):
        return super().batch_update(
            self.table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, record_id: str):
        return super().delete(self.table_name, record_id)

    def batch_delete(self, record_ids: List[str]):
        return super().batch_delete(self.table_name, record_ids)

    def __repr__(self) -> str:
        return "<Table base_id={} table_name={}>".format(self.base_id, self.table_name)
