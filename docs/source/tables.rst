Working with Tables
==============================

.. include:: substitutions.rst


.. note::
    Airtable imposes a `rate limit <https://airtable.com/developers/web/api/rate-limits>`__
    of 5 QPS per base. If you exceed that limit, their API will return 429 errors for a moment.
    By default, pyAirtable will retry 429 errors up to five times, but retrieving many pages
    of records might take several seconds. Read more at :func:`pyairtable.retry_strategy`.


Supported Endpoints
-------------------

The Airtable API exposes a number of endpoints for manipulating data within tables.
The grid below maps Airtable's official API endpoints to this library's methods.

.. list-table::
   :header-rows: 1

   * - Airtable Endpoint
     - pyAirtable Method
   * - `Get a record <https://airtable.com/developers/web/api/get-record>`_
     - :meth:`~pyairtable.Table.get`
   * - `Get all records <https://airtable.com/developers/web/api/list-records>`_
     - :meth:`~pyairtable.Table.all`
   * - `Get matching records <https://airtable.com/developers/web/api/list-records>`_
     - :meth:`all(formula=...) <pyairtable.Table.all>`
   * - `Get first match <https://airtable.com/developers/web/api/list-records>`_
     - :meth:`~pyairtable.Table.first`
   * - `Create a record <https://airtable.com/developers/web/api/create-records>`_
     - :meth:`~pyairtable.Table.create`
   * - `Update a record <https://airtable.com/developers/web/api/update-record>`_
     - :meth:`~pyairtable.Table.update`
   * - `Replace a record <https://airtable.com/developers/web/api/update-record>`_
     - :meth:`update(replace=True) <pyairtable.Table.update>`
   * - `Delete a record <https://airtable.com/developers/web/api/delete-record>`_
     - :meth:`~pyairtable.Table.delete`
   * - `Create multiple records <https://airtable.com/developers/web/api/create-records>`_
     - :meth:`~pyairtable.Table.batch_create`
   * - `Update multiple records <https://airtable.com/developers/web/api/update-multiple-records>`_
     - :meth:`~pyairtable.Table.batch_update`
   * - `Upsert multiple records <https://airtable.com/developers/web/api/update-multiple-records>`_
     - :meth:`~pyairtable.Table.batch_upsert`
   * - `Delete multiple records <https://airtable.com/developers/web/api/delete-multiple-records>`_
     - :meth:`~pyairtable.Table.batch_delete`


Fetching Records
-----------------

:meth:`~pyairtable.Table.iterate`

Iterate over a set of records of size ``page_size``, up until ``max_records`` or end of table.

.. code-block:: python

  >>> for records in table.iterate(page_size=100, max_records=1000):
  ...     print(records)
  ...
  [{'id': 'rec123asa23', 'fields': {'Last Name': 'Alfred', 'Age': 84}, ...}, ...]
  [{'id': 'rec123asa23', 'fields': {'Last Name': 'Jameson', 'Age': 42}, ...}, ...]

:meth:`~pyairtable.Table.all`

This method returns a single list with all records in a table. Note that under the
hood it uses :meth:`~pyairtable.Table.iterate` to fetch records so it might make
multiple requests.

.. code-block:: python

  >>> table.all(sort=["Name", "-Age"])
  [{'id': 'rec123asa23', 'fields': {'Last Name': 'Alfred', 'Age': 84}, ...}, ...]


Parameters
**********

Airtable's API offers a variety of options to control how you fetch data.

Most options in the Airtable API (e.g. ``sort``, ``fields``, etc.)
have a corresponding keyword argument that can be used with fetching methods
like :meth:`~pyairtable.Table.iterate` or :meth:`~pyairtable.Table.all`.


.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Keyword Argument
     - Notes
   * - ``max_records``
     - |kwarg_max_records|
   * - ``sort``
     - |kwarg_sort|
   * - ``view``
     - |kwarg_view|
   * - ``page_size``
     - |kwarg_page_size|
   * - ``formula``
     - |kwarg_formula|
   * - ``fields``
     - |kwarg_fields|
   * - ``cell_format``
     - |kwarg_cell_format|
   * - ``user_locale``
     - |kwarg_user_locale|
   * - ``time_zone``
     - |kwarg_time_zone|
   * - ``return_fields_by_field_id``
        .. versionadded:: 1.3.0
     - |kwarg_return_fields_by_field_id|


Formulas
********

The :mod:`pyairtable.formulas` module provides functionality to help you compose
`Airtable formulas <https://support.airtable.com/hc/en-us/articles/203255215-Formula-field-reference>`_.

* :func:`~pyairtable.formulas.match` checks field values from a Python ``dict``:

  .. code-block:: python

      >>> from pyairtable.formulas import match
      >>> formula = match({"First Name": "John", "Age": 21})
      >>> formula
      "AND({First Name}='John',{Age}=21)"
      >>> table.first(formula=formula)
      {"id": "recUwKa6lbNSMsetH", "fields": {"First Name": "John", "Age": 21}}

* :func:`~pyairtable.formulas.to_airtable_value` converts a Python value
  to an expression that can be included in a formula:

  .. code-block:: python

      >>> from pyairtable.formulas import to_airtable_value
      >>> to_airtable_value(1)
      1
      >>> to_airtable_value(datetime.date.today())
      '2023-06-13'

For more on generating formulas, look over the :mod:`pyairtable.formulas` API reference.


Retries
*******

As of 2.0.0, the default behavior is to retry requests up to five times if the Airtable API responds with
a 429 status code, indicating you've exceeded their per-base QPS limit. To adjust the default behavior,
you can use the :func:`~pyairtable.retry_strategy` function.


Creating Records
-----------------

:meth:`~pyairtable.Table.create`

Creates a single record from a dictionary representing the table's fields.

.. code-block:: python

  >>> table.create({'Name': 'John'})
  {'id': 'rec123asa23', 'fields': {'Name': 'John', ...}}


:meth:`~pyairtable.Table.batch_create`

Create multiple records from a list of :class:`~pyairtable.api.types.WritableFields` dicts.

.. code-block:: python

  >>> table.batch_create([{'Name': 'John'}, ...])
  [{'id': 'rec123asa23', 'fields': {'Name': 'John'}}, ...]


Updating Records
-----------------

:meth:`~pyairtable.Table.update`

Updates a single record for the provided ``record_id`` using a
dictionary representing the table's fields.

.. code-block:: python

  >>> table.update('recwPQIfs4wKPyc9D', {"Age": 21})
  [{'id': 'recwPQIfs4wKPyc9D', 'fields': {"Name": "John", "Age": 21}}, ...]


:meth:`~pyairtable.Table.batch_update`

Update multiple records from a list of :class:`~pyairtable.api.types.UpdateRecordDict`.

.. code-block:: python

  >>> table.batch_update([{"id": "recwPQIfs4wKPyc9D", "fields": {"Name": "Matt"}}, ...])
  [{'id': 'recwPQIfs4wKPyc9D', 'fields': {"Name": "Matt", ...}}, ...]


:meth:`~pyairtable.Table.batch_upsert`

.. versionadded:: 1.5.0

Batch upsert (create or update) records from a list of records. For details on the behavior
of this Airtable API endpoint, see `Update multiple records`_.

.. code-block:: python

  >>> table.batch_upsert(
  ...     [{"id": "recwPQIfs4wKPyc9D", "fields": {"Name": "Matt"}}, ...],
  ...     key_fields=["Name"]
  ... )
  [{'id': 'recwPQIfs4wKPyc9D', 'fields': {'Name': 'Matt', ...}}, ...]


Deleting Records
-----------------

:meth:`~pyairtable.Table.delete`

Deletes a single record using the provided ``record_id``.

.. code-block:: python

  >>> table.delete('recwPQIfs4wKPyc9D')
  {'deleted': True, 'id': 'recwPQIfs4wKPyc9D'}

:meth:`~pyairtable.Table.batch_delete`

Batch delete records using a list of record ids.

.. code-block:: python

  >>> table.batch_delete(['recwPQIfs4wKPyc9D', 'recwAcQdqwe21asdf'])
  [{'deleted': True, 'id': 'recwPQIfs4wKPyc9D'},
   {'deleted': True, 'id': 'recwAcQdqwe21asdf'}]


Return Values
-------------

This library will return records as :class:`~pyairtable.api.types.RecordDict`.

.. code-block:: python

  >>> table.all()
  [
      {
          'id': 'recwPQIfs4wKPyc9D',
          'createdTime': '2017-03-14T22:04:31.000Z'
          'fields': {
              'Name': 'Alice',
          },
      },
      {
          'id': 'rechOLltN9SpPHq5o',
          'createdTime': '2017-03-20T15:21:50.000Z'
          'fields': {
              'Name': 'Bob',
          },
      },
      {
          'id': 'rec5eR7IzKSAOBHCz',
          'createdTime': '2017-08-05T21:47:52.000Z'
          'fields': {
              'Name': 'Carol',
          },
      }
  ]
