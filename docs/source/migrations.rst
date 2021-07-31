
0.x Migration
**************

When writing pyAirtable, we made some significant changes to the api.

The objective here was to introduce a simpler api that's more closely aligned with Airtable Api's patterns.


.. list-table:: Changes
   :widths: 40 60
   :header-rows: 1

   * - 0.x (airtable-python-wrapper)
     - 1.0 (pyAirtable)
   * - ``get()``
     - ``get()``
   * - ``get_iter()``
     - ``iterate()``
   * - ``get_all()``
     - TBD: ``list()`` or ``all()``
   * - ``search()``
     - ``m = match({"Name" : "X"}`` ``get_all(formula=m)``
   * - ``match(**kwargs)``
     - ``m = match({"Name" : "X"}`` ``get_all(formula=m)``
   * - ``insert()``
     - ``create()``
   * - ``update()``
     - ``update()``
   * - ``replace()``
     - use ``update(replace=True)``
   * - ``delete()``
     - ``delete()``
