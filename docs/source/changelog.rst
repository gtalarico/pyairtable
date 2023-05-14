=========
Changelog
=========

1.5.0
------

Release Date: 2023-05-15

* Add support for Airtable's upsert operation (see :ref:`Updating Records`).
  - `PR #255 <https://github.com/gtalarico/pyairtable/pull/255>`_.
* Fix ``return_fields_by_field_id`` in :meth:`~pyairtable.api.Api.batch_create` and :meth:`~pyairtable.api.Api.batch_update`.
  - `PR #252 <https://github.com/gtalarico/pyairtable/pull/252>`_.
* Fix ORM crash when Airtable returned additional fields.
  - `PR #250 <https://github.com/gtalarico/pyairtable/pull/250>`_.
* Use POST for URLs that are longer than the 16k character limit set by the Airtable API.
  - `PR #247 <https://github.com/gtalarico/pyairtable/pull/247>`_.
* Added ``endpoint_url=`` param to :class:`~pyairtable.api.Table`, :class:`~pyairtable.api.Base`, :class:`~pyairtable.api.Api`.
  - `PR #243 <https://github.com/gtalarico/pyairtable/pull/243>`_.
* Added ORM :class:`~pyairtable.orm.fields.LookupField`.
  - `PR #182 <https://github.com/gtalarico/pyairtable/pull/182>`_.
* Dropped support for Python 3.6 (reached end of life 2021-12-23)
  - `PR #213 <https://github.com/gtalarico/pyairtable/pull/213>`_.

1.4.0
------

Release Date: 2022-12-14

* Added :ref:`Retrying` ()
* Misc fix in sleep for batch requests `PR #180 <https://github.com/gtalarico/pyairtable/pull/180>`_.

1.3.0
------

Release Date: 2022-08-23

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
