
Getting Started
======================================


.. include:: substitutions.rst


Installation
------------

Add the `pyairtable <https://pypi.org/project/pyairtable>`_ library to your project just as you would any other:

.. code-block:: shell

    $ pip install pyairtable


Connecting to Airtable
----------------------

To begin, you will need an API key or a personal access token. If you do not have one yet,
see `the Airtable guide to personal access tokens <https://airtable.com/developers/web/guides/personal-access-tokens>`_.
`Airtable has deprecated API keys <https://support.airtable.com/docs/airtable-api-key-deprecation-notice>`_
and they will stop working with the API in February 2024. Both can be used interchangeably with this library.

This library will not persist your access token anywhere. Your access token should be securely stored.
A common method is to `store it as an environment variable <https://www.twilio.com/blog/2017/01/how-to-set-environment-variables.html>`_
and load it using ``os.environ``.

The :class:`~pyairtable.Api` class represents a connection to Airtable, while the
:class:`~pyairtable.Table` class exposes methods for retrieving, creating, and modifying
records in Airtable:

.. code-block:: python

    >>> import os
    >>> from pyairtable import Api
    >>> api = Api(os.environ['AIRTABLE_API_KEY'])
    >>> table = api.table('appExampleBaseId', 'tblExampleTableId')
    >>> table.all()
    [
        {
            "id": "rec5eR7IzKSAOBHCz",
            "createdTime": "2017-03-14T22:04:31.000Z",
            "fields": {
                "Name": "Alice",
                "Exail": "alice@example.com"
            }
        }
    ]
    >>> table.create({"Name": "Bob"})
    {
        "id": "recwAcQdqwe21asdf",
        "createdTime": "...",
        "fields": {"Name": "Bob"}
    }
    >>> table.update("recwAcQdqwe21asdf", {"Name": "Robert"})
    {
        "id": "recwAcQdqwe21asdf",
        "createdTime": "...",
        "fields": {"Name": "Robert"}
    }
    >>> table.delete("recwAcQdqwe21asdf")
    {'id': 'recwAcQdqwe21asdf', 'deleted': True}

For more details on the available classes and methods check out the :doc:`api` section.


Supported Endpoints
-------------------

The Airtable API exposes a number of endpoints for manipulating data within tables.
The grid below shows a comparison of the methods provided by this library alongside
the official API equivalents.

.. list-table::
   :widths: 30 30 40
   :header-rows: 1

   * - Endpoint
     - pyAirtable
     - Airtable API
   * - `Get a record <https://airtable.com/developers/web/api/get-record>`_
     - :meth:`~pyairtable.Table.get`
     - ``GET baseId/tableId/recordId``
   * - `Get all records <https://airtable.com/developers/web/api/list-records>`_
     - :meth:`~pyairtable.Table.all`
     - ``GET baseId/tableId``
   * - `Get matching records <https://airtable.com/developers/web/api/list-records>`_
     - :meth:`all(formula=...) <pyairtable.Table.all>`
     - ``GET baseId/tableId?filterByFormula=...``
   * - `Get first match <https://airtable.com/developers/web/api/list-records>`_
     - :meth:`~pyairtable.Table.first`
     - ``GET baseId/tableId?maxRecords=1``
   * - `Create a record <https://airtable.com/developers/web/api/create-records>`_
     - :meth:`~pyairtable.Table.create`
     - ``POST baseId/tableId``
   * - `Update a record <https://airtable.com/developers/web/api/update-record>`_
     - :meth:`~pyairtable.Table.update`
     - ``PATCH baseId/tableId/recordId``
   * - `Replace a record <https://airtable.com/developers/web/api/update-record>`_
     - :meth:`update(replace=True) <pyairtable.Table.update>`
     - ``PUT baseId/tableId/recordId``
   * - `Delete a record <https://airtable.com/developers/web/api/delete-record>`_
     - :meth:`~pyairtable.Table.delete`
     - ``DELETE baseId/tableId/recordId``
   * - `Create multiple records <https://airtable.com/developers/web/api/create-records>`_
     - :meth:`~pyairtable.Table.batch_create`
     - ``POST baseId/tableId``
   * - `Update multiple records <https://airtable.com/developers/web/api/update-multiple-records>`_
     - :meth:`~pyairtable.Table.batch_update`
     - ``PATCH baseId/tableId``
   * - `Upsert multiple records <https://airtable.com/developers/web/api/update-multiple-records>`_
     - :meth:`~pyairtable.Table.batch_upsert`
     - ``PATCH baseId/tableId``
   * - `Delete multiple records <https://airtable.com/developers/web/api/delete-multiple-records>`_
     - :meth:`~pyairtable.Table.batch_delete`
     - ``DELETE baseId/tableId``


Fetching Records
-----------------

.. warning:: |warn_rate_limit|

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


Creating Records
-----------------

:meth:`~pyairtable.Table.create`

Creates a single record from a dictionary representing the table's fields.

.. code-block:: python

  >>> table.create({'Name': 'John'})
  {'id': 'rec123asa23', 'fields': {'Name': 'John', ...}}


:meth:`~pyairtable.Table.batch_create`

Create multiple records from a list of :class:`~pyairtable.api.types.Fields` dicts.

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
