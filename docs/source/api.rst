.. include:: substitutions.rst

Airtable Api
============

Overview
********

This client offers three classes you can use to access the Airtable Api:

* :class:`~airtable.api.Table` - represents an Airtable **Table**
* :class:`~airtable.api.Base` - represents an Airtable **Base**
* :class:`~airtable.api.Api` - represents an Airtable **Api**

The interfaces of these are nearly identical, the main difference
is if ``base_id`` and ``table_id`` are provided on initialization or on calls.

For example, the three ``all()`` calls below would return the same result:

.. code-block:: python

  from airtable import Api, Base, Table

  api = Api('apikey')
  api.all('base_id', 'table_name')

  base = Base('apikey', 'base_id')
  base.all('table_name')

  table = Table('apikey', 'table_name', 'base_id')
  table.all()

Interface
***********

The table below shows a comparison of the methods used in the library compared
with the official API equivalent.

.. list-table:: pyAirtable Api
   :widths: 30 30 40
   :header-rows: 1

   * - Description
     - pyAirtable
     - Airtable Api
   * - Retrieve a single Record
     - ``get()``
     - ``GET baseId/recordId``
   * - Iterate over record pages
     - ``iterate()``
     - ``GET baseId/``
   * - Get all records
     - ``all()``
     - ``GET baseId/``
   * - Get all matches
     - ``all(formula=match(...)``
     - ``GET baseId/?filterByFormula=...``
   * - Get first match
     - ``first(formula=match(...)``
     - ``GET baseId/?filterByFormula=...&maxRecords=1``
   * - Create record
     - ``create()``
     - ``POST baseId/``
   * - Update a record
     - ``update()``
     - ``PUT baseId/``
   * - Replace a record
     - ``update(replace=True)``
     - ``PATCH base/``
   * - Delete a record
     - ``delete()``
     - ``DELETE baseId/``


Fetching Records
-----------------

:meth:`~airtable.api.Table.iterate`

Iterate over a set of records of size ``page_size``, up until ``max_records`` or end of
table, whichever is shorter.

.. code-block:: python

  >>> for records in table.iterate(page_size=100, max_records=1000):
  ...     print(records)
  [{id:'rec123asa23', fields': {'Last Name': 'Alfred', "Age": 84}, ...}, ... ]
  [{id:'rec123asa23', fields': {'Last Name': 'Jameson', "Age": 42}, ...}, ... ]

:meth:`~airtable.api.Table.all`

This method returns a single list with all records in a table. Note that under the
hood it uses :meth:`~airtable.api.Table.iterate` to fetch records so multiple requests might be made.

.. code-block:: python

  >>> table.all(sort=["First Name", "-Age"]):
  [{id:'rec123asa23', fields': {'Last Name': 'Alfred', "Age": 84}, ...}, ... ]


Creating Records
-----------------

:meth:`~airtable.api.Table.create`

Creates a single record from a dictionary representing the table's fields.

.. code-block:: python

  >>> table.create({'First Name': 'John'})
  {id:'rec123asa23', fields': {'First Name': 'John', ...}}


:meth:`~airtable.api.Table.batch_create`

Batch create records from a list of dictionaries representing the table's fields.

.. code-block:: python

  >>> table.batch_create([{'First Name': 'John'}, ...])
  [{id:'rec123asa23', fields': {'First Name': 'John', ...}}, ...]


Updating Records
-----------------

:meth:`~airtable.api.Table.update`

Updates a single record for the provided ``record_id`` using a
dictionary representing the table's fields.

.. code-block:: python

  >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
  [{id:'recwPQIfs4wKPyc9D', fields': {"First Name": "John", "Age": 21, ...}}, ...]


:meth:`~airtable.api.Table.batch_update`

Batch update records from a list of records.

.. code-block:: python

  >>> table.batch_update([{"id": "recwPQIfs4wKPyc9D", "fields": {"First Name": "Matt"}}, ...])
  [{id:'recwPQIfs4wKPyc9D', fields': {"First Name": "Matt", "Age": 21, ...}}, ...]


Deleting Records
-----------------

:meth:`~airtable.api.Table.delete`

Deletes a single record using the provided ``record_id``.

.. code-block:: python

  >>> airtable.delete('recwPQIfs4wKPyc9D')
  { "deleted": True, ... }

:meth:`~airtable.api.Table.batch_delete`

Batch delete records using a list of record ids.

.. code-block:: python

  >>> airtable.batch_delete(['recwPQIfs4wKPyc9D', 'recwAcQdqwe21as'])
  [  { "deleted": True, ... }, ... ]


Return Values
-------------

Return Values: when records are returned,
will most often be alist of Airtable records (dictionary) in a format as shown below.

.. code-block:: python

  >>> table.all()
  ... [{
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


The :class:`~airtable.api.Base` class is similar to :class:`~airtable.api.Table`, the main difference is that .
`table_name` is not provided during initialization. Instead, it can be
specified on each request.

.. code-block:: python

  >>> base = Base('appEioitPbxI72w06', 'apikey')
  >>> base.all('Contacts)
  [{id:'rec123asa23', fields': {'Last Name': 'Alfred', "Age": 84}, ... ]


-------------------------

Classes
*******

Api
-----
.. autoclass:: airtable.api.Api
    :members:

Base
-----
.. autoclass:: airtable.api.Base
    :members:

Table
-----
.. autoclass:: airtable.api.Table
    :members:



Parameters
**********

Airtable offers a variety of options to control how you fetch data.

Most options in the Airtable Api (eg. ``sort``, ``fields``, etc)
have a corresponding ``kwargs`` that can be used with fetching methods like :meth:`~airtable.api.Table.iterate`.


.. list-table:: Title
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter
     - Airtable Option
     - Notes
   * - ``max_records``
     - ``maxRecords``
     - |kwarg_max_records|
   * - ``sort``
     - ``sort``
     - |kwarg_sort|
   * - ``view``
     - ``view``
     - |kwarg_view|
   * - ``page_size``
     - ``pageSize``
     - |kwarg_page_size|
   * - ``formula``
     - ``filterByFormula``
     - |kwarg_formula|
   * - ``fields``
     - ``fields``
     - |kwarg_fields|


Formulas
********

The formula module provides funcionality to help you compose airtable formulas.
For more information see `Airtable Formula Reference <https://support.airtable.com/hc/en-us/articles/203255215-Formula-field-reference>`_


.. code-block:: python

  >>> table = Table("apikey", "base_id", "Contact")
  >>> formula = match({"First Name": "John", "Age": 21})
  >>> table.first(formula=formula)
  {"id": "recUwKa6lbNSMsetH", "fields": {"First Name": "John", "Age": 21}}
  >>> formula
  "AND({First Name}='John',{Age}=21)"

.. autofunction:: airtable.formulas.match


Raw Formulas
------------

This module also includes many lower level functions you
can use if you want to compose formulas:


.. autofunction:: airtable.formulas.EQUAL
.. autofunction:: airtable.formulas.FIELD
.. autofunction:: airtable.formulas.AND


