
Getting Started
======================================


.. include:: substitutions.rst


Installation
------------

Add the `pyAirtable <https://pypi.org/project/pyairtable>`_ library to your project just as you would any other:

.. code-block:: shell

    $ pip install pyairtable


Access tokens
-------------

To begin, you will need an API key or a personal access token. If you do not have one yet,
see the Airtable guide to `personal access tokens <https://airtable.com/developers/web/guides/personal-access-tokens>`__.

This library will not persist your access token anywhere. Your access token should be securely stored.
A common method is to `store it as an environment variable <https://www.twilio.com/blog/2017/01/how-to-set-environment-variables.html>`_
and load it using ``os.environ``.

.. note::

    `Airtable has deprecated API keys <https://support.airtable.com/docs/airtable-api-key-deprecation-notice>`_
    and they will stop working with in February 2024. Both can be used with pyAirtable,
    and our code/docs may still refer to "API keys" instead of "access tokens".


Quickstart
----------

The :class:`~pyairtable.Api` class represents a connection to Airtable, while the
:class:`~pyairtable.Table` class exposes methods for retrieving, creating, and modifying
records in Airtable:

.. code-block:: python

    >>> import os
    >>> from pyairtable import Api
    >>> api = Api(os.environ['AIRTABLE_API_KEY'])
    >>> table = api.get_table('appExampleBaseId', 'tblExampleTableId')
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

See :doc:`tables` for more details on how to get and set data in Airtable.
