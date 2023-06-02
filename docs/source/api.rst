.. include:: substitutions.rst

API Reference
=============


Api
*******

.. autoclass:: pyairtable.api.Api
    :members:


Base
*******

.. autoclass:: pyairtable.api.Base
    :members:


Table
*******

.. autoclass:: pyairtable.api.Table
    :members:


Retrying
********

.. versionadded:: 1.4.0

You may provide an instance of ``urllib3.util.Retry`` to configure retrying behaviour,
or you can use :func:`~pyairtable.api.retrying.retry_strategy` to quickly generate a
``Retry`` instance with reasonable defaults (which you can adjust).

.. note:: for backwards-compatibility, the default behavior is to not retry (`retry_strategy=None`).
  This may change in future releases.

Out of the box, :func:`~pyairtable.api.retrying.retry_strategy` will retry a request several times
if it receives a 429 (which indicates you've exceeded Airtable's limit of 5 QPS per base) or
if it receives a potentially transient server-side error (500, 502, 503, or 504).

.. code-block:: python

  from pyairtable import Api, retry_strategy
  api = Api('auth_token', retry_strategy=retry_strategy())


.. autofunction:: pyairtable.api.retrying.retry_strategy



Parameters
**********

Airtable offers a variety of options to control how you fetch data.

Most options in the Airtable API (e.g. ``sort``, ``fields``, etc.)
have a corresponding keyword argument that can be used with fetching methods
like :meth:`~pyairtable.api.Table.iterate` or :meth:`~pyairtable.api.Table.all`.


.. list-table::
   :widths: 35 65
   :header-rows: 1

   * - Keyword Argument
     - Notes
   * - ``max_records``
     - |kwarg_max_records|
   * - ``sort``
     - |kwarg_sort|
   * - ``view``
     - |kwarg_view|
   * - ``page_size``
     - |kwarg_page_size|
   * - ``formula``
     - |kwarg_formula|
   * - ``fields``
     - |kwarg_fields|
   * - ``cell_format``
     - |kwarg_cell_format|
   * - ``user_locale``
     - |kwarg_user_locale|
   * - ``time_zone``
     - |kwarg_time_zone|
   * - ``return_fields_by_field_id``
        .. versionadded:: 1.3.0
     - |kwarg_return_fields_by_field_id|


Formulas
********


The formula module provides functionality to help you compose Airtable formulas.
For more information see `Airtable Formula Reference <https://support.airtable.com/hc/en-us/articles/203255215-Formula-field-reference>`_

Match
---------------

:func:`~pyairtable.formulas.match` helps you build a formula to check for equality
against a Python dictionary:

.. code-block:: python

  >>> import pyairtable
  >>> from pyairtable.formulas import match
  >>> table = pyairtable.Api("auth_token").table("base_id", "Contact")
  >>> formula = match({"First Name": "John", "Age": 21})
  >>> formula
  "AND({First Name}='John',{Age}=21)"
  >>> table.first(formula=formula)
  {"id": "recUwKa6lbNSMsetH", "fields": {"First Name": "John", "Age": 21}}

.. autofunction:: pyairtable.formulas.match


Formula Helpers
---------------

.. autofunction:: pyairtable.formulas.to_airtable_value
.. autofunction:: pyairtable.formulas.escape_quotes


Raw Formulas
------------


This module also includes many lower level functions you
can use if you want to compose formulas:


.. autofunction:: pyairtable.formulas.EQUAL
.. autofunction:: pyairtable.formulas.FIELD
.. autofunction:: pyairtable.formulas.AND
.. autofunction:: pyairtable.formulas.OR
.. autofunction:: pyairtable.formulas.FIND
.. autofunction:: pyairtable.formulas.IF
.. autofunction:: pyairtable.formulas.STR_VALUE
.. autofunction:: pyairtable.formulas.LOWER


Types
*******

.. automodule:: pyairtable.api.types
    :members:

Utilities
***********

.. automodule:: pyairtable.utils
    :members:
