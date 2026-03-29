.. include:: _warn_latest.rst
.. include:: _substitutions.rst


Metadata
==============

The Airtable API gives you the ability to list all of your bases, tables, fields, and views.
pyAirtable allows you to inspect and interact with this metadata in your bases.

There may be parts of the Airtable API which are not supported below;
you can always use :meth:`Api.request <pyairtable.Api.request>` to call them directly.


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

.. automethod:: pyairtable.Table.schema
    :noindex:


Modifying existing schema
-----------------------------

To modify a table or field, you can modify portions of its schema object directly
and call ``save()``, as shown below. The Airtable API only allows changing certain
properties; these are enumerated in the API reference for each schema class.
For example, :class:`~pyairtable.models.schema.TableSchema` allows changing the name,
description, and date dependency configuration.

.. code-block:: python

    >>> schema = table.schema()
    >>> schema.name = "Renamed"
    >>> schema.save()
    >>> field = schema.field("Name")
    >>> field.name = "Label"
    >>> field.description = "The primary field on the table"
    >>> field.save()

To add or replace the date dependency configuration on a table, you can use the shortcut method
:meth:`TableSchema.set_date_dependency <pyairtable.models.schema.TableSchema.set_date_dependency>`.


Creating schema elements
-----------------------------

The following methods allow creating bases, tables, or fields:

.. automethod:: pyairtable.Api.create_base
    :noindex:

.. automethod:: pyairtable.Workspace.create_base
    :noindex:

.. automethod:: pyairtable.Workspace.move_base
    :noindex:

.. automethod:: pyairtable.Base.create_table
    :noindex:

.. automethod:: pyairtable.Table.create_field
    :noindex:


Deleting schema elements
-----------------------------

|enterprise_only|

The Airtable API does not allow deleting tables or fields, but it does allow
deleting workspaces, bases, and views. pyAirtable supports the following methods:

To delete a :class:`~pyairtable.Workspace`:

    >>> ws = api.workspace("wspmhESAta6clCCwF")
    >>> ws.delete()

To delete a :class:`~pyairtable.Base`:

    >>> base = api.base("appMxESAta6clCCwF")
    >>> base.delete()

To delete a view, first retrieve its :class:`~pyairtable.models.schema.ViewSchema`:

    >>> vw = table.schema().view("View Name")
    >>> vw.delete()
