
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


Api Key
*******

Your Airtable API key should be securely stored. 
A common way to do this, is to `store it as an environment variable <https://www.twilio.com/blog/2017/01/how-to-set-environment-variables.html>`_, 
and load it using ``os.environ``:

.. code-block:: python

    import os
    api_key = os.environ["AIRTABLE_API_KEY"]



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
    [ {"id": "rec5eR7IzKSAOBHCz", "fields": { ... }}]
    >>> table.create({"Foo": "Bar"})
    {"id": "recwAcQdqwe21as", "fields": { "Foo": "Bar" }}]
    >>> table.update("recwAcQdqwe21as", {"Foo": "Foo"})
    {"id": "recwAcQdqwe21as", "fields": { "Foo": "Foo" }}]
    >>> table.delete("recwAcQdqwe21as")
    True

For more details on the available classes and methods check out the :doc:`api` section.
