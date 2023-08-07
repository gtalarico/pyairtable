.. include:: _warn_latest.rst
.. include:: _substitutions.rst


Migration Guide
*****************


Migrating from 1.x to 2.0
============================

With the 2.0 release, we've made some breaking changes to the pyAirtable API. These are summarized below.
You can read more about the rationale behind these changes in `#257 <https://github.com/gtalarico/pyairtable/issues/257>`_,
and you see a list of changes and new features in the :ref:`Changelog`.

ApiAbstract removed
-----------------------

We've removed the ``pyairtable.api.abstract`` module. If you had code which inherited from ``ApiAbstract``,
you will need to refactor it. We recommend taking an instance of :class:`~pyairtable.Api` as a
constructor parameter, and using that to construct :class:`~pyairtable.Table` instances as needed.

Changes to Api, Base, and Table
-----------------------------------

:class:`~pyairtable.Api`, :class:`~pyairtable.Base`, and :class:`~pyairtable.Table`
no longer inherit from the same base class. Each has its own scope of responsibility and has
methods which refer to the other classes as needed. See :ref:`Getting Started`.

For a period of time, the constructor for :class:`~pyairtable.Base` and :class:`~pyairtable.Table`
will remain backwards-compatible with the previous approach (passing in ``str`` values),
but doing so will produce deprecation warnings.

See below for supported and unsupported patterns:

.. code-block:: python

    # The following are supported:
    >>> api = Api(api_key, timeout=..., retry_strategy=..., endpoint_url=...)
    >>> base = api.base(base_id)  # [str]
    >>> base = Base(api, base_id)  # [Api, str]
    >>> table = base.table(table_name)  # [str]
    >>> table = api.table(base_id, table_name)  # [str, str]
    >>> table = Table(None, base, table_name)  # [None, Base, str]

    # The following are still supported but will issue a DeprecationWarning:
    >>> base = Base(api_key, base_id)  # [str, str]
    >>> table = Table(api_key, base_id, table_name)  # [str, str, str]

    # The following will raise a TypeError for mixing str & instances:
    >>> table = Table(api_key, base, table_name)  # [str, Base, str]
    >>> table = Table(api, base_id, table_name)  # [Api, str, str]

    # The following will raise a TypeError. We do this proactively
    # to avoid situations where self.api and self.base don't align.
    >>> table = Table(api, base_id, table_name)  # [Api, Base, str]

You may need to change how your code looks up some pieces of connection metadata; for example:

.. list-table::
    :header-rows: 1

    * - Method/attribute in 1.5
      - Method/attribute in 2.0
    * - ``base.base_id``
      - :data:`base.id <pyairtable.Base.id>`
    * - ``table.table_name``
      - :data:`table.name <pyairtable.Table.name>`
    * - ``table.get_base()``
      - :data:`table.base <pyairtable.Table.base>`
    * - ``table.base_id``
      - :data:`table.base.id <pyairtable.Base.id>`
    * - ``table.table_url``
      - :meth:`table.url <pyairtable.Table.url>`
    * - ``table.get_record_url()``
      - :meth:`table.record_url() <pyairtable.Table.record_url>`

There is no fully exhaustive list of changes; please refer to
:ref:`the API documentation <Module: pyairtable>` for a list of available methods and attributes.

Retry by default
----------------

* By default, the library will retry requests up to five times if it receives
  a 429 status code from Airtable, indicating the base has exceeded its QPS limit.

Changes to the ORM
------------------

* :meth:`Model.all <pyairtable.orm.Model.all>` and :meth:`Model.first <pyairtable.orm.Model.first>`
  return instances of the model class instead of returning dicts.
* :class:`~pyairtable.orm.fields.LinkField` now defaults to ``lazy=False``. The first time your code
  accesses the field, it will perform one or more API calls to retrieve field data for linked records.
  You can disable this by passing ``lazy=True`` when creating the field.

Changes to types
----------------

* All functions and methods in this library have full type annotations that will pass ``mypy --strict``.
  See the :ref:`types <Module: pyairtable.api.types>` module for more information on the types this library accepts and returns.

batch_upsert has a different return type
--------------------------------------------

* :meth:`~pyairtable.Table.batch_upsert` now returns the full payload from the Airtable API,
  as opposed to just the list of records (with no indication of which were created or updated).
  See :class:`~pyairtable.api.types.UpsertResultDict` for more details.


Found a problem?
--------------------

While these breaking changes were intentional, it is very possible that the 2.0 release has bugs.
Please take a moment to :ref:`read our contribution guidelines <contributing>` before submitting an issue.


------


Migrating from 0.x to 1.0
============================

**Airtable Python Wrapper** was renamed to **pyAirtable** starting on its first major release, ``1.0.0``.
The docs for the older release will remain `on Read the Docs <https://airtable-python-wrapper.readthedocs.io/>`__,
the source code on `this branch <https://github.com/gtalarico/airtable-python-wrapper>`__.
The last ``0.x`` release will remain available on `PyPI <https://pypi.org/project/airtable-python-wrapper/>`__.

You can read about the reasons behind the renaming `here <https://github.com/gtalarico/airtable-python-wrapper/issues/125#issuecomment-891439661>`__.


New Features in 1.0
-------------------

* Type Annotations
* Simpler API
* Formulas
* ORM Models

API Changes in 1.0
------------------

We used this new major release to make a few breaking changes:

* Introduced a simpler API that's more closely aligned with Airtable API's patterns.
* Created more a flexible API (:class:`~pyairtable.Api`, :class:`~pyairtable.Base`, :class:`~pyairtable.Table`)


.. list-table:: Changes
   :widths: 35 65
   :header-rows: 1

   * - 0.x (airtable-python-wrapper)
     - 1.0 (pyAirtable)
   * - ``Airtable()``
     - :class:`~pyairtable.Api`, :class:`~pyairtable.Base`, :class:`~pyairtable.Table`
   * - ``get()``
     - ``get()``
   * - ``get_iter()``
     - ``iterate()``
   * - ``get_all()``
     - ``all()``
   * - ``search()``
     - ``all(formula=match({"Name" : "X"})``
   * - ``match(**kwargs)``
     - ``first(formula=match({"Name" : "X"})``
   * - ``insert()``
     - ``create()``
   * - ``update()``
     - ``update()``
   * - ``replace()``
     - use ``update(replace=True)``
   * - ``delete()``
     - ``delete()``
