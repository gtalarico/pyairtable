
0.x Migration
**************


**Airtable Python Wrapper** was renamed to **pyAirtable** starting on its first major release, ``1.0.0``.
The docs for the older release will remain `on Read the Docs <https://airtable-python-wrapper.readthedocs.io/>`_,
the source code on `this branch <https://github.com/gtalarico/airtable-python-wrapper>`_.
The last ``0.x`` release will remain available on `PYPI <https://pypi.org/project/airtable-python-wrapper/>`_.

You can read about the reasons behind the renaming `here <https://github.com/gtalarico/airtable-python-wrapper/issues/125#issuecomment-891439661>`_.

New Features
------------

* Type Annotations
* Simpler Api
* Formulas
* ORM Models

API Changes
------------

We used this new major release to make a few breaking changes:

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
