=========
Changelog
=========

.. warning::
    Looking for airtable-python-wrapper changelog? See :doc:`migrations`.

1.5.0 (unreleased)
-------------------
* Added ``endpoint_url=`` param to :class:`~pyairtable.api.Table`, :class:`~pyairtable.api.Base`, :class:`~pyairtable.api.Api`
  - `PR #243 <https://github.com/gtalarico/pyairtable/pull/243>`_.

1.4.0
------
* Added :ref:`Retrying` ()
* Misc fix in sleep for batch requests `PR #180 <https://github.com/gtalarico/pyairtable/pull/180>`_.

1.3.0
------
* Added new ``LOWER`` formula - `PR #171 <https://github.com/gtalarico/pyairtable/pull/171>`_. See updated :ref:`Formulas`.
* Added ``match(..., match_any=True)`` to :meth:`~pyairtable.formulas.match`
* Added ``return_fields_by_field_id`` in :meth:`~pyairtable.api.Api.get`

1.2.0
------

Release Date: 2022-07-09

* Fixed missing rate limit in :meth:`~pyairtable.api.Api.batch_update` - `PR #162 <https://github.com/gtalarico/pyairtable/pull/162>`_.
* Added support for new parameter `return_fields_by_field_id` - `PR #161 <https://github.com/gtalarico/pyairtable/pull/161>`_. See updated :ref:`Parameters`.
* Added new ``OR`` formula - `PR #148 <https://github.com/gtalarico/pyairtable/pull/148>`_. See updated :ref:`Formulas`.

1.1.0
------

Release Date: 2022-02-21

* Added support for ``cellFormat`` - `PR #140 <https://github.com/gtalarico/pyairtable/pull/140>`_.  See updated :ref:`Parameters`.


1.0.0
------

Release Date: 2021-08-11

* pyAirtable rewrite for 1.x - see :doc:`migrations`.

0.15.3
------

Release Date: 2021-07-26
