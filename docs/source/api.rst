.. include:: substitutions.rst

Api
************


Classes
==============

.. autoclass:: airtable.api.AirtableApi
    :members:
    :private-members:

.. autoclass:: airtable.api.Table
    :members:
    :undoc-members:

.. autoclass:: airtable.api.Base
    :members:
    :undoc-members:


Parameters
==================

Airtable offers a variety of options to control how you fetch data.

Each option in the Airtable Api (eg. `sort`, `fields`, etc)
has a corresponding kwargs that can be used with fetching methods like :any:`Table.iterate`.


.. list-table:: Title
   :widths: 25 25 50
   :header-rows: 1

   * - Parameter
     - Airtable Option
     - Notes
   * - ``max_records``
     - ``maxRecords``
     - |kwarg_max_records|
   * - ``sort``
     - ``sort``
     - |kwarg_sort|
   * - ``view``
     - ``view``
     - |kwarg_view|
   * - ``page_size``
     - ``pageSize``
     - |kwarg_page_size|
   * - ``formula``
     - ``filterByFormula``
     - |kwarg_formula|
   * - ``fields``
     - ``fields``
     - |kwarg_fields|


Formulas
==============

For more information see `Airtable Formula Reference <https://support.airtable.com/hc/en-us/articles/203255215-Formula-field-reference>`_


.. automodule:: airtable.formulas
    :members:

