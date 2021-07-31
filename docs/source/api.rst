.. include:: substitutions.rst

Api
===

Overview
********

This client offers three classes you can use to access the Airtable Api:

* :class:`~airtable.api.Table` - represents a specific Airtable Table
* :class:`~airtable.api.Base` - represents a specific Airtable Base
* :class:`~airtable.api.Api` - represents a generic Airtable Api session

The interfaces of these are nearly identical, the main difference
is if ``base_id`` and ``table_id`` is provided on initialization or on method calls.

  >>> from airtable import Api, Base, Table
  >>> api = Api('apikey')
  >>> api.get_all('base_id', 'table_name')
  [ ... ]
  >>> base = Base('base_id', 'apikey')
  >>> base.get_all('table_name')
  [ ... ]
  >>> table = Table('table_name, 'base_id', 'apikey')
  >>> table.get_all()

We tried to keep the library's api close to the actual Api, but made
selective changes:

.. list-table:: pyAirtable Api
   :widths: 30 30 40
   :header-rows: 1

   * - Description
     - pyAirtable
     - Airtable Api
   * - Retrieve a single Record
     - ``get()``
     - ``GET base/recordId``
   * - Iterate over record pages
     - ``iterate()``
     - ``GET base/``
   * - Get all records
     - TBD: ``list()`` or ``all()``
     - ``GET base/``
   * - Get all matches
     - ``get_all(formula=match({"Name" : "X"})``
     - ``GET base/?filterByFormula={Name}='X'``
   * - Get first match
     - ``first(formula=match({"Name" : "X"})``
     - ``GET base/?filterByFormula={Name}='X'&maxRecords=1``
   * - Create record
     - ``create()``
     - ``POST base/``
   * - Update a record
     - ``update()``
     - ``PUT base/``
   * - Replace a record
     - use ``update(replace=True)``
     - ``PATCH base/``
   * - Delete a record
     - ``delete()``
     - ``DELETE base/``

.. automodule:: airtable.api.table


The :class:`~airtable.api.Base` class is similar to :class:`~airtable.api.Table`, the main difference is that .
`table_name` is not provided during initialization. Instead, it can be
specified on each request.

  >>> base = Base('appEioitPbxI72w06', 'apikey')
  >>> base.get_all('Contacts)
  [{id:'rec123asa23', fields': {'Last Name': 'Alfred', "Age": 84}, ... ]


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

Most options in the Airtable Api (eg. `sort`, `fields`, etc)
have a corresponding ``kwargs`` that can be used with fetching methods like :any:`Table.iterate`.


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

For more information see `Airtable Formula Reference <https://support.airtable.com/hc/en-us/articles/203255215-Formula-field-reference>`_


.. automodule:: airtable.formulas
.. autofunction:: airtable.formulas.match


Raw Formulas
------------

This module also includes many lower level functions you
can use if you want to compose formulas:


.. autofunction:: airtable.formulas.EQUAL
.. autofunction:: airtable.formulas.FIELD
.. autofunction:: airtable.formulas.AND


