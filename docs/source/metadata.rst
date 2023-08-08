.. include:: _warn_latest.rst
.. include:: _substitutions.rst


Metadata
==============

The Airtable API gives you the ability to list all of your bases, tables, fields, and views.
pyAirtable allows you to inspect and interact with this metadata through the following methods:

All of the methods above return complex nested data structures, some of which
have their own convenience methods for searching their contents, such as
:meth:`TableSchema.field() <pyairtable.models.schema.TableSchema.field>`.
You'll find more detail in the API reference for :mod:`pyairtable.models.schema`.

.. automethod:: pyairtable.Api.bases
    :noindex:

.. automethod:: pyairtable.Base.info
    :noindex:

.. automethod:: pyairtable.Base.schema
    :noindex:

.. automethod:: pyairtable.Base.tables
    :noindex:

.. automethod:: pyairtable.Table.schema
    :noindex:
