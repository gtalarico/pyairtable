"""
The :class:`Table` class represents and Airtable Table.
With this class, `base_id`, `table_name`, and `api_key` are provided during initialization.
All requests from this instance will be bound this table.

>>> from airtable import Table
>>> table = Table('appEioitPbxI72w06', 'Contacts', 'keyapikey')


Fetching Records
****************

:any:`Table.iterate`
-------------------------

Iterate over a set of records of size `page_size`, up until `max_records` or end of
table, whichever is shorted.

>>> for records in table.iterate(page_size=100, max_records=1000):
...     print(records)
[{id:'rec123asa23', fields': {'Last Name': 'Alfred', "Age": 84}, ...}, ... ]
[{id:'rec123asa23', fields': {'Last Name': 'Jameson', "Age": 42}, ...}, ... ]

:any:`Table.get_all`
--------------------

This method returns a single list with all records in a table. Note that under the
hood it uses :any:`Table.iterate` to fetch records so multiple requests might be made.

>>> table.get_all(sort=["First Name", "-Age"]):
[{id:'rec123asa23', fields': {'Last Name': 'Alfred', "Age": 84}, ...}, ... ]


Creating Records
****************

:any:`Table.create`
-------------------

>>> table.create({'First Name': 'John'})
{id:'rec123asa23', fields': {'First Name': 'John', ...}}

:any:`Table.batch_create`
-------------------------

>>> table.batch_create([{'First Name': 'John'}, ...])
[{id:'rec123asa23', fields': {'First Name': 'John', ...}}, ...]

Updating Records
****************

:any:`Table.update`
-------------------

>>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
[{id:'recwPQIfs4wKPyc9D', fields': {"First Name": "John", "Age": 21, ...}}, ...]


Batch Update Records
--------------------

TODO


Deleting Records
****************

:any:`Table.delete`
-------------------

>>> airtable.delete('recwPQIfs4wKPyc9D')
{ "deleted": True, ... }

:any:`Table.batch_delete`
-------------------------

>>> airtable.batch_delete(['recwPQIfs4wKPyc9D', 'recwAcQdqwe21as'])
[ { "deleted": True, ... }, ... ]

------------------------------------------------------------------------

Return Values
**************

Return Values: when records are returned,
will most often be alist of Airtable records (dictionary) in a format as shown below.

>>> [{
...     "records": [
...         {
...             "id": "recwPQIfs4wKPyc9D",
...             "fields": {
...                 "COLUMN_ID": "1",
...             },
...             "createdTime": "2017-03-14T22:04:31.000Z"
...         },
...         {
...             "id": "rechOLltN9SpPHq5o",
...             "fields": {
...                 "COLUMN_ID": "2",
...             },
...             "createdTime": "2017-03-20T15:21:50.000Z"
...         },
...         {
...             "id": "rec5eR7IzKSAOBHCz",
...             "fields": {
...                 "COLUMN_ID": "3",
...             },
...             "createdTime": "2017-08-05T21:47:52.000Z"
...         }
...     ],
...     "offset": "rec5eR7IzKSAOBHCz"
... }, ... ]

"""

from typing import List
from .api import ApiBase


class Table(ApiBase):
    """
    Airtable Table - Similar to :class:`~airtable.api.Api` but
    ``base_id`` and ``table_name`` are provided on init and not needed on method calls.
    """

    def __init__(self, base_id: str, table_name: str, api_key: str, *, timeout=None):
        """
        Args:
            base_id: |arg_base_id|
            table_name: |arg_table_name|
        """
        self.base_id = base_id
        self.table_name = table_name
        super().__init__(api_key, timeout=timeout)

    @property
    def table_url(self):
        return super().get_table_url(self.base_id, self.table_name)

    def get_record_url(self, record_id: str):
        """
        Same as :meth:`Api.get_record_url <airtable.api.Api.get_record_url>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._get_record_url(self.base_id, self.table_name, record_id)

    def get(self, record_id: str):
        """
        Same as :meth:`Api.get <airtable.api.Api.get>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._get_record(self.base_id, self.table_name, record_id)

    def iterate(self, **options):
        """
        Same as :meth:`Api.iterate <airtable.api.Api.iterate>`
        but without ``base_id`` and ``table_name`` arg.
        """
        gen = super()._iterate(self.base_id, self.table_name, **options)
        for i in gen:
            yield i

    def first(self, **options):
        """
        Same as :meth:`Api.first <airtable.api.Api.first>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._first(self.base_id, self.table_name, **options)

    def get_all(self, **options):
        """
        Same as :meth:`Api.get_all <airtable.api.Api.get_all>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._get_all(self.base_id, self.table_name, **options)

    def create(self, fields: dict, typecast=False):
        """
        Same as :meth:`Api.create <airtable.api.Api.create>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._create(self.base_id, self.table_name, fields, typecast=typecast)

    def batch_create(self, records, typecast=False):
        """
        Same as :meth:`Api.batch_create <airtable.api.Api.batch_create>`
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
        Same as :meth:`Api.update <airtable.api.Api.update>`
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
        Same as :meth:`Api.batch_update <airtable.api.Api.batch_update>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._batch_update(
            self.base_id, self.table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, record_id: str):
        """
        Same as :meth:`Api.delete <airtable.api.Api.delete>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._delete(self.base_id, self.table_name, record_id)

    def batch_delete(self, record_ids: List[str]):
        """
        Same as :meth:`Api.batch_delete <airtable.api.Api.batch_delete>`
        but without ``base_id`` and ``table_name`` arg.
        """
        return super()._batch_delete(self.base_id, self.table_name, record_ids)

    def __repr__(self) -> str:
        return "<Table base_id={} table_name={}>".format(self.base_id, self.table_name)
