.. include:: _warn_latest.rst
.. include:: _substitutions.rst


Metadata
==============

The Airtable API gives you the ability to list all of your bases, tables, fields, and views.
pyAirtable allows you to inspect and interact with the metadata in your bases.


Reading schemas
-----------------------------

All of the methods below return complex nested data structures, some of which
have their own convenience methods for searching their contents, such as
:meth:`TableSchema.field() <pyairtable.models.schema.TableSchema.field>`.
You'll find more detail in the API reference for :mod:`pyairtable.models.schema`.

.. automethod:: pyairtable.Api.bases
    :noindex:

.. automethod:: pyairtable.Base.schema
    :noindex:

.. automethod:: pyairtable.Base.tables
    :noindex:

.. automethod:: pyairtable.Base.shares
    :noindex:

.. automethod:: pyairtable.Table.schema
    :noindex:


Modifying schemas
-----------------------------

The following methods allow you to modify parts of the Airtable schema.
There may be parts of the pyAirtable API which are not supported below;
you can always use :meth:`Api.request <pyairtable.Api.request>` to
call them directly.

.. automethod:: pyairtable.Api.create_base
    :noindex:

.. automethod:: pyairtable.Api.delete_base
    :noindex:

.. automethod:: pyairtable.Base.create_table
    :noindex:

.. automethod:: pyairtable.Table.create_field
    :noindex:


Enterprise information
-----------------------------

pyAirtable exposes a number of classes and methods for interacting with enterprise organizations.
The following methods are only available on an `Enterprise plan <https://airtable.com/pricing>`__.
If you call one of them against a base that is not part of an enterprise workspace, Airtable will
return a 404 error, and pyAirtable will add a reminder to the exception to check your billing plan.

.. automethod:: pyairtable.Api.enterprise
    :noindex:

.. automethod:: pyairtable.Base.info
    :noindex:

.. automethod:: pyairtable.Workspace.info
    :noindex:

.. automethod:: pyairtable.Enterprise.info
    :noindex:
