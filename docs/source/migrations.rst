
0.x Migration
**************

In addition to new modules like :doc:`orm` and :ref:`Formulas` , 1.0 also
includes a few breaking changes to the previous api.

The objective here was to introduce a simpler api that's more closely aligned with Airtable Api's patterns.

.. list-table:: Title
   :widths: 25 25 50
   :header-rows: 1

   * - 1.x
     - 0.x
     - Description
   * - ``Airtable()``
     - ``Table()``, ``Base()``, ``Api()``
     - Airtable Api Class
   * - ``iterate()``
     - ``get_iter()``
     - Iterate over record pages
   * - ``create``
     - ``insert``
     - Creates new record, aligns with Airtable Api naming
   * - ``replace``
     - ``update(replace=True)``
     - Replace record with provided, simplify API.
   * - ``match()``
     - removed - use ``get_all(formula='')`` or ``first(formula=)``
     - ... TODO
   * - ``search()``
     - removed - use ``get_all(formula='')`` or ``first(formula)``
     - ... TODO

