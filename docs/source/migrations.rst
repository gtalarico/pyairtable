Migration Guide
*****************


Migrating from 1.x to 2.0
============================

With the 2.0 release, we've made some breaking changes to the pyAirtable API. These are summarized below.
You can read more about the rationale behind these changes in `#257 <https://github.com/gtalarico/pyairtable/issues/257>`_.

New Features in 2.0
-------------------

* The :ref:`ORM` module now has support for all Airtable field types.

API Changes in 2.0
------------------

* :class:`~pyairtable.api.Api`, :class:`~pyairtable.api.Base`, and :class:`~pyairtable.api.Table`
  no longer inherit from the same base class. Each has its own scope of responsibility and has
  methods which refer to the other classes as needed. See :ref:`Getting Started`.

* We've removed the `pyairtable.api.abstract` module. If you had code which inherited from `ApiAbstract`,
  you will need to refactor it. We recommend taking an instance of :class:`~pyairtable.api.Api` as a
  constructor parameter, and using that to construct :class:`~pyairtable.api.Table` instances as needed.

* :meth:`Model.all <pyairtable.orm.Model.all>` and :meth:`Model.first <pyairtable.orm.Model.first>`
  return instances of the model class instead of returning dicts.

* All functions and methods in this library have full type annotations that will pass ``mypy --strict``.
  See the :ref:`Types` section for more information on the types available to use in this library.


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
* Simpler Api
* Formulas
* ORM Models

API Changes in 1.0
------------------

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
