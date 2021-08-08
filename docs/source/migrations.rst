
0.x Migration
**************

Background
----------

**Airtable Python Wrapper** was renamed to **pyAirtable** starting on its first major release, ``1.0.0``.
The docs for the older release will remain here `here <https://github.com/gtalarico/airtable-python-wrapper>`_,
and docs `here <https://airtable-python-wrapper.readthedocs.io/en/airtable-python-wrapper>`_, and the last final release
will remain available on `PYPI <https://pypi.org/project/airtable-python-wrapper/>`_.

You can read about the reasons behind the renaming `here <https://github.com/gtalarico/airtable-python-wrapper/issues/125#issuecomment-891439661>`_.

API Changes
------------

When writing pyAirtable, we a few changes to the api:

* Introduced a simpler api that's more closely aligned with Airtable Api's patterns.
* Created more a flexible API (:class:`~pyairtable.api.Api`, :class:`~pyairtable.api.Base`, :class:`~pyairtable.api.Table`)


.. list-table:: Changes
   :widths: 35 65
   :header-rows: 1

   * - 0.x (airtable-python-wrapper)
     - 1.0 (pyAirtable)
   * - ``Airtable()``
     - :class:`~pyairtable.api.Api`, :class:`~pyairtable.api.Base`, :class:`~pyairtable.api.Table`
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
