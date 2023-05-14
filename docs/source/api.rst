.. include:: substitutions.rst

Airtable Api
============

Overview
********

This client offers three classes you can use to access the Airtable Api:

* :class:`~pyairtable.api.Table` - represents an Airtable **Table**
* :class:`~pyairtable.api.Base` - represents an Airtable **Base**
* :class:`~pyairtable.api.Api` - represents an Airtable **Api**

The interfaces of these are nearly identical, the main difference
is if ``base_id`` and ``table_id`` are provided on initialization or on calls.

For example, the three ``all()`` calls below would return the same result:

.. code-block:: python

  from pyairtable import Api, Base, Table

  api = Api('auth_token')
  api.all('base_id', 'table_name')

  base = Base('auth_token', 'base_id')
  base.all('table_name')

  table = Table('auth_token', 'base_id', 'table_name')
  table.all()

Interface
***********

The table below shows a comparison of the methods used in the library compared
with the official API equivalent.

.. list-table:: pyAirtable Api
   :widths: 30 30 40
   :header-rows: 1

   * - Type
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
     - ``PATCH baseId/``
   * - Replace a record
     - ``update(replace=True)``
     - ``PUT base/``
   * - Delete a record
     - ``delete()``
     - ``DELETE baseId/``

Examples
***********

Examples below use the :class:`~pyairtable.api.Table` Api for conciseness -
all methods are available for all three interfaces (``Api``, ``Base``, and ``Table``).

Fetching Records
-----------------

:meth:`~pyairtable.api.Table.iterate`

Iterate over a set of records of size ``page_size``, up until ``max_records`` or end of
table, whichever is shorter.

.. code-block:: python

  >>> for records in table.iterate(page_size=100, max_records=1000):
  ...     print(records)
  [{'id': 'rec123asa23', 'fields': {'Last Name': 'Alfred', 'Age': 84}, ...}, ...]
  [{'id': 'rec123asa23', 'fields': {'Last Name': 'Jameson', 'Age': 42}, ...}, ...]

:meth:`~pyairtable.api.Table.all`

This method returns a single list with all records in a table. Note that under the
hood it uses :meth:`~pyairtable.api.Table.iterate` to fetch records so multiple requests might be made.

.. code-block:: python

  >>> table.all(sort=["First Name", "-Age"]):
  [{'id': 'rec123asa23', 'fields': {'Last Name': 'Alfred', 'Age': 84}, ...}, ...]


Creating Records
-----------------

:meth:`~pyairtable.api.Table.create`

Creates a single record from a dictionary representing the table's fields.

.. code-block:: python

  >>> table.create({'First Name': 'John'})
  {'id': 'rec123asa23', 'fields': {'First Name': 'John', ...}}


:meth:`~pyairtable.api.Table.batch_create`

Batch create records from a list of dictionaries representing the table's fields.

.. code-block:: python

  >>> table.batch_create([{'First Name': 'John'}, ...])
  [{'id': 'rec123asa23', 'fields': {'First Name': 'John'}}, ...]


Updating Records
-----------------

:meth:`~pyairtable.api.Table.update`

Updates a single record for the provided ``record_id`` using a
dictionary representing the table's fields.

.. code-block:: python

  >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
  [{'id': 'recwPQIfs4wKPyc9D', 'fields': {"First Name": "John", "Age": 21}}, ...]


:meth:`~pyairtable.api.Table.batch_update`

Batch update records from a list of records.

.. code-block:: python

  >>> table.batch_update([{"id": "recwPQIfs4wKPyc9D", "fields": {"First Name": "Matt"}}, ...])
  [{'id': 'recwPQIfs4wKPyc9D', 'fields': {"First Name": "Matt", ...}}, ...]


:meth:`~pyairtable.api.Table.batch_upsert`

.. versionadded:: 1.5.0

Batch upsert (create or update) records from a list of records. For details on the behavior
of this Airtable API endpoint, see `Update multiple records <https://airtable.com/developers/web/api/update-multiple-records#request-performupsert-fieldstomergeon>`_.

.. code-block:: python

  >>> table.batch_upsert(
  ...     [{"id": "recwPQIfs4wKPyc9D", "fields": {"First Name": "Matt"}}, ...],
  ...     key_fields=["First Name"]
  ... )
  [{'id': 'recwPQIfs4wKPyc9D', 'fields': {'First Name': 'Matt', 'Age': 21, ...}}, ...]


Deleting Records
-----------------

:meth:`~pyairtable.api.Table.delete`

Deletes a single record using the provided ``record_id``.

.. code-block:: python

  >>> table.delete('recwPQIfs4wKPyc9D')
  {'deleted': True, 'id': 'recwPQIfs4wKPyc9D'}

:meth:`~pyairtable.api.Table.batch_delete`

Batch delete records using a list of record ids.

.. code-block:: python

  >>> table.batch_delete(['recwPQIfs4wKPyc9D', 'recwAcQdqwe21asdf'])
  [{'deleted': True, 'id': 'recwPQIfs4wKPyc9D'},
   {'deleted': True, 'id': 'recwAcQdqwe21asdf'}]


Return Values
-------------

Return Values: when records are returned,
will most often be a list of Airtable records (dictionary) in a format as shown below.

.. code-block:: python

  >>> table.all()
  [
      {
          "records": [
              {
                  "id": "recwPQIfs4wKPyc9D",
                  "fields": {
                      "COLUMN_ID": "1",
                  },
                  "createdTime": "2017-03-14T22:04:31.000Z"
              },
              {
                  "id": "rechOLltN9SpPHq5o",
                  "fields": {
                      "COLUMN_ID": "2",
                  },
                  "createdTime": "2017-03-20T15:21:50.000Z"
              },
              {
                  "id": "rec5eR7IzKSAOBHCz",
                  "fields": {
                      "COLUMN_ID": "3",
                  },
                  "createdTime": "2017-08-05T21:47:52.000Z"
              }
          ],
          "offset": "rec5eR7IzKSAOBHCz"
      },
      ...
  ]


The :class:`~pyairtable.api.Base` class is similar to :class:`~pyairtable.api.Table`, the main difference is that
`table_name` is not provided during initialization. Instead, it can be
specified on each request.

.. code-block:: python

  >>> base = Base('auth_token', 'base_id')
  >>> base.all('Contacts')
  [{'id': 'rec123asa23', 'fields': {'Last Name': 'Alfred', 'Age': 84}, ...]


-------------------------

Classes
*******

Api
-----

.. versionadded:: 1.0.0
.. autoclass:: pyairtable.api.Api
  :members:

Base
-----

.. versionadded:: 1.0.0
.. autoclass:: pyairtable.api.Base
    :members:

Table
-----
.. versionadded:: 1.0.0
.. autoclass:: pyairtable.api.Table
    :members:


Retrying
********

.. versionadded:: 1.4.0

You may provide an instance of ``urllib3.util.Retry`` to configure
retrying behaviour.

The library also provides :func:`~pyairtable.api.retrying.retry_strategy` to quickly generate a
``Retry`` instance with reasonable defaults that you can use as-is or with tweaks.

.. note:: for backwards-compatibility, the default behavior is no retry (`retry_strategy=None`).
  This may change in future releases.

Default Retry Strategy

.. code-block:: python

  from pyairtable import Api, retry_strategy
  api = Api('auth_token', retry_strategy=retry_strategy())


Adjusted Default Strategy

.. code-block:: python

  from pyairtable import Api, retry_strategy
  api = Api('auth_token', retry_strategy=retry_strategy(total=3))

Custom Retry

.. code-block:: python

  from pyairtable import Api, retry_strategy
  from urllib3.util import Retry

  myRetry = Retry(**kwargs)
  api = Api('auth_token', retry_strategy=myRetry)


.. autofunction:: pyairtable.api.retrying.retry_strategy



Parameters
**********

Airtable offers a variety of options to control how you fetch data.

Most options in the Airtable Api (e.g. ``sort``, ``fields``, etc.)
have a corresponding ``kwargs`` that can be used with fetching methods like :meth:`~pyairtable.api.Table.iterate`.


.. list-table::
   :widths: 25 25 50
   :header-rows: 1

   * - Keyword Argument
     - Airtable Parameter
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
   * - ``cell_format``
     - ``cellFormat``
     - |kwarg_cell_format|
   * - ``user_locale``
     - ``userLocale``
     - |kwarg_user_locale|
   * - ``time_zone``
     - ``timeZone``
     - |kwarg_time_zone|
   * - ``return_fields_by_field_id``
        .. versionadded:: 1.3.0
     - ``returnFieldsByFieldId``
     - |kwarg_return_fields_by_field_id|


Formulas
********

.. versionadded:: 1.0.0

The formula module provides functionality to help you compose Airtable formulas.
For more information see `Airtable Formula Reference <https://support.airtable.com/hc/en-us/articles/203255215-Formula-field-reference>`_

Match
---------------

:func:`~pyairtable.formulas.match` helps you build a formula to check for equality
against a Python dictionary:

.. code-block:: python

  >>> from pyairtable import Table
  >>> from pyairtable.formulas import match
  >>> table = Table("auth_token", "base_id", "Contact")
  >>> formula = match({"First Name": "John", "Age": 21})
  >>> table.first(formula=formula)
  {"id": "recUwKa6lbNSMsetH", "fields": {"First Name": "John", "Age": 21}}
  >>> formula
  "AND({First Name}='John',{Age}=21)"

.. autofunction:: pyairtable.formulas.match


Formula Helpers
---------------

.. autofunction:: pyairtable.formulas.to_airtable_value
.. autofunction:: pyairtable.formulas.escape_quotes


Raw Formulas
------------

.. versionadded:: 1.0.0

This module also includes many lower level functions you
can use if you want to compose formulas:


.. autofunction:: pyairtable.formulas.EQUAL
.. autofunction:: pyairtable.formulas.FIELD
.. autofunction:: pyairtable.formulas.AND
.. autofunction:: pyairtable.formulas.OR
.. autofunction:: pyairtable.formulas.FIND
.. autofunction:: pyairtable.formulas.IF
.. autofunction:: pyairtable.formulas.STR_VALUE
.. autofunction:: pyairtable.formulas.LOWER
