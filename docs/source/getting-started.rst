
Getting Started
======================================


.. include:: substitutions.rst


Installation
************

.. code-block:: shell

    $ pip install pyairtable

.. warning::
    Looking for **airtable-python-wrapper**? Check out :doc:`migrations`.

_______________________________________________


Authorization Token
*******************

Airtable accepts two types of authentication tokens: Api Keys, and Personal Access tokens.
Your auth token should be securely stored.
A common way to do this, is to `store it as an environment variable <https://www.twilio.com/blog/2017/01/how-to-set-environment-variables.html>`_,
and load it using ``os.environ``:

.. code-block:: python

    import os
    api_key = os.environ["AIRTABLE_API_KEY"]

.. Note:
     Personal access tokens are a new, more secure way to grant API access to your Airtable data.
     They can create multiple tokens, grant them access to specific bases, and manage them individually.

     Api keys are scheduled to be deprecated in upcoming versions.

Quickstart
**********

The easiest way to use this client is to use the :class:`~pyairtable.api.Table` class to fetch
or update your records:

.. code-block:: python

    >>> import os
    >>> from pyairtable import Table
    >>> api_key = os.environ['AIRTABLE_API_KEY']
    >>> table = Table(api_key, 'base_id', 'table_name')
    >>> table.all()
    [
        {
            "id": "rec5eR7IzKSAOBHCz",
            "createdTime": "2017-03-14T22:04:31.000Z",
            "fields": {...}
        }
    ]
    >>> table.create({"Foo": "Bar"})
    {
        "id": "recwAcQdqwe21asdf",
        "createdTime": "...",
        "fields": {"Foo": "Bar"}
    }
    >>> table.update("recwAcQdqwe21asdf", {"Foo": "Foo"})
    {
        "id": "recwAcQdqwe21asdf",
        "createdTime": "...",
        "fields": {"Foo": "Foo"}
    }
    >>> table.delete("recwAcQdqwe21asdf")
    {'id': 'recwAcQdqwe21asdf', 'deleted': True}

For more details on the available classes and methods check out the :doc:`api` section.
