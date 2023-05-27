
Getting Started
======================================


.. include:: substitutions.rst


Installation
************

.. code-block:: shell

    $ pip install pyairtable


API keys
*******************

You need an `API key <https://support.airtable.com/docs/creating-and-using-api-keys-and-access-tokens>`_
or a `personal access token <https://airtable.com/developers/web/guides/personal-access-tokens>`_
to access the Airtable API. The two can be used interchangeably with this library, but API keys
`will stop working on February 1, 2024 <https://support.airtable.com/docs/airtable-api-key-deprecation-notice>`__.

pyAirtable will not persist your API key; it is your responsibility to store and load it securely.
A common practice is to store it as an environment variable and load it with ``os.environ``.


Quickstart
**********

The following example will load an API key from the environment, connect to Airtable,
and interact with records in a particular table.

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
