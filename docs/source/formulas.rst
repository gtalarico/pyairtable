Building Formulas
=================

pyAirtable lets you construct formulas at runtime using Python syntax,
and will convert those formula objects into the appropriate strings when
sending them to the Airtable API.


Basics
--------------------------

In cases where you want to find records with fields matching a computed value,
this library provides the :func:`~pyairtable.formulas.match` function, which
returns a formula that can be passed to methods like :func:`Table.all <pyairtable.Table.all>`:

.. autofunction:: pyairtable.formulas.match
    :noindex:


Compound conditions
--------------------------

Formulas and conditions can be chained together if you need to create
more complex criteria:

    >>> from datetime import date
    >>> from pyairtable.formulas import AND, GTE, Field, match
    >>> formula = AND(
    ...     match("Customer", 'Alice'),
    ...     GTE(Field("Delivery Date"), date.today())
    ... )
    >>> formula
    AND(EQ(Field('Customer'), 'Alice'),
        GTE(Field('Delivery Date'), datetime.date(2023, 12, 10)))
    >>> str(formula)
    "AND({Customer}='Alice', {Delivery Date}>=DATETIME_PARSE('2023-12-10'))"

pyAirtable has support for the following comparisons:

    .. list-table::

       * - :class:`pyairtable.formulas.EQ`
         - ``lval = rval``
       * - :class:`pyairtable.formulas.NE`
         - ``lval != rval``
       * - :class:`pyairtable.formulas.GT`
         - ``lval > rval``
       * - :class:`pyairtable.formulas.GTE`
         - ``lval >= rval``
       * - :class:`pyairtable.formulas.LT`
         - ``lval < rval``
       * - :class:`pyairtable.formulas.LTE`
         - ``lval <= rval``

These are also implemented as convenience methods on all instances
of :class:`~pyairtable.formulas.Formula`, so that the following are equivalent:

    >>> EQ(Field("Customer"), "Alice")
    >>> match({"Customer": "Alice"})
    >>> Field("Customer").eq("Alice")

pyAirtable exports ``AND``, ``OR``, ``NOT``, and ``XOR`` for chaining conditions.
You can also use Python operators to modify and combine formulas:

    >>> from pyairtable.formulas import match
    >>> match({"Customer": "Bob"}) & ~match({"Product": "TEST"})
    AND(EQ(Field('Customer'), 'Bob'),
        NOT(EQ(Field('Product'), 'TEST')))

    .. list-table::
       :header-rows: 1

       * - Python operator
         - `Airtable equivexpressionalent <https://support.airtable.com/docs/formula-field-reference#logical-operators-and-functions-in-airtable>`__
       * - ``lval & rval``
         - ``AND(lval, rval)``
       * - ``lval | rval``
         - ``OR(lval, rval)``
       * - ``~rval``
         - ``NOT(rval)``
       * - ``lval ^ rval``
         - ``XOR(lval, rval)``

Calling functions
--------------------------

pyAirtable also exports functions that act as placeholders for calling
Airtable formula functions:

    >>> from pyairtable.formulas import Field, GTE, DATETIME_DIFF, TODAY
    >>> formula = GTE(DATETIME_DIFF(TODAY(), Field("Purchase Date"), "days"), 7)
    >>> str(formula)
    "DATETIME_DIFF(TODAY(), {Purchase Date}, 'days')>=7"

All supported functions are listed in the :mod:`pyairtable.formulas` API reference.
