
Getting Started
======================================


.. include:: substitutions.rst


Installation
************

.. code-block:: shell

    $ pip install pyairtable

_______________________________________________


Api Key
*******

Your Api Key should be kept secure and should likely not be saved in your code.
A common way to store and used it in your code is to save the key in your environment
and load it

.. code-block:: python

    import os
    api_key = os.environ["AIRTABLE_API_KEY"]



Quickstart
**********

The easiest way to use this client is to the :class:`~airtable.api.Table` class to fetch
or update your records:

.. code-block:: python

    >>> import os
    >>> from airtable import Table
    >>> api_key = os.environ['AIRTABLE_API_KEY']
    >>> table = Table('base_id', 'base_id', api_key)
    >>> table.all()
    [ {"id": "rec5eR7IzKSAOBHCz", "fields": { ... }}]
    >>> table.create({"Foo": "Bar"})
    {"id": "recwAcQdqwe21as", "fields": { "Foo": "Bar" }}]
    >>> table.update("recwAcQdqwe21as", {"Foo": "Foo"})
    {"id": "recwAcQdqwe21as", "fields": { "Foo": "Foo" }}]
    >>> table.delete("recwAcQdqwe21as")
    True

For more details on all the available classes and methods checkout the :doc:`api` section.
