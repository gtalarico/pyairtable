
In addition to new modules like :doc:`orm` and :ref:`Formulas` , 1.0 also
made a few breaking changes to the previous api:

* ``Airtable()`` -> ``Table``, ``Base``
* ``airtable.get_iter()`` -> ``table.iterate()``
* ``airtable.get_all()`` -> ``table.get_all()``
* ``airtable.insert()`` -> ``table.create()``
* ``airtable.replace()`` -> ``table.update(replace=True)``

Removed Methods:
* ``airtable.match()`` -> Use ``table.get_all()`` or ``table.first()`` with formula filter
* ``airtable.search()`` -> same as above


Keep `insert`?
