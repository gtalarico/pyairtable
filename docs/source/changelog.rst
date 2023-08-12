=========
Changelog
=========

2.1.0 (2023-08-18)
------------------------

* Added classes and methods for managing :ref:`webhooks`.
  - `PR #291 <https://github.com/gtalarico/pyairtable/pull/291>`_.
* Added compatibility with Pydantic 2.0.
  - `PR #288 <https://github.com/gtalarico/pyairtable/pull/288>`_.

2.0.0 (2023-07-31)
------------------------

See :ref:`Migrating from 1.x to 2.0` for detailed migration notes.

* Added :class:`~pyairtable.models.Comment` class; see :ref:`Commenting on Records`.
  - `PR #282 <https://github.com/gtalarico/pyairtable/pull/282>`_.
* :meth:`~pyairtable.Table.batch_upsert` now returns the full payload from the Airtable API.
  - `PR #281 <https://github.com/gtalarico/pyairtable/pull/281>`_.
* :ref:`ORM` module is no longer experimental and has a stable API.
  - `PR #277 <https://github.com/gtalarico/pyairtable/pull/277>`_.
* Added :meth:`Model.batch_save <pyairtable.orm.Model.batch_save>`
  and :meth:`Model.batch_delete <pyairtable.orm.Model.batch_delete>`.
  - `PR #274 <https://github.com/gtalarico/pyairtable/pull/277>`_.
* Added :meth:`Api.whoami <pyairtable.Api.whoami>` method.
  - `PR #273 <https://github.com/gtalarico/pyairtable/pull/273>`_.
* pyAirtable will automatically retry requests when throttled by Airtable's QPS.
  - `PR #272 <https://github.com/gtalarico/pyairtable/pull/272>`_.
* ORM Meta attributes can now be defined as callables.
  - `PR #268 <https://github.com/gtalarico/pyairtable/pull/268>`_.
* Removed ``ApiAbstract``.
  - `PR #267 <https://github.com/gtalarico/pyairtable/pull/267>`_.
* Implemented strict type annotations on all functions and methods.
  - `PR #263 <https://github.com/gtalarico/pyairtable/pull/263>`_.
* Return Model instances, not dicts, from
  :meth:`Model.all <pyairtable.orm.Model.all>` and :meth:`Model.first <pyairtable.orm.Model.first>`.
  - `PR #262 <https://github.com/gtalarico/pyairtable/pull/262>`_.
* Dropped support for Python 3.7.
  - `PR #261 <https://github.com/gtalarico/pyairtable/pull/261>`_.
* :ref:`ORM` supports all Airtable field types.
  - `PR #260 <https://github.com/gtalarico/pyairtable/pull/260>`_.

1.5.0 (2023-05-15)
-------------------------

* Add support for Airtable's upsert operation (see :ref:`Updating Records`).
  - `PR #255 <https://github.com/gtalarico/pyairtable/pull/255>`_.
* Fix ``return_fields_by_field_id`` in :meth:`~pyairtable.Api.batch_create` and :meth:`~pyairtable.Api.batch_update`.
  - `PR #252 <https://github.com/gtalarico/pyairtable/pull/252>`_.
* Fix ORM crash when Airtable returned additional fields.
  - `PR #250 <https://github.com/gtalarico/pyairtable/pull/250>`_.
* Use POST for URLs that are longer than the 16k character limit set by the Airtable API.
  - `PR #247 <https://github.com/gtalarico/pyairtable/pull/247>`_.
* Added ``endpoint_url=`` param to :class:`~pyairtable.Table`, :class:`~pyairtable.Base`, :class:`~pyairtable.Api`.
  - `PR #243 <https://github.com/gtalarico/pyairtable/pull/243>`_.
* Added ORM :class:`~pyairtable.orm.fields.LookupField`.
  - `PR #182 <https://github.com/gtalarico/pyairtable/pull/182>`_.
* Dropped support for Python 3.6 (reached end of life 2021-12-23)
  - `PR #213 <https://github.com/gtalarico/pyairtable/pull/213>`_.

1.4.0 (2022-12-14)
-------------------------

* Added :func:`pyairtable.retry_strategy`.
* Misc fix in sleep for batch requests `PR #180 <https://github.com/gtalarico/pyairtable/pull/180>`_.

1.3.0 (2022-08-23)
-------------------------

* Added new ``LOWER`` formula - `PR #171 <https://github.com/gtalarico/pyairtable/pull/171>`_. See :mod:`pyairtable.formulas`.
* Added ``match(..., match_any=True)`` to :meth:`~pyairtable.formulas.match`
* Added ``return_fields_by_field_id`` in :meth:`~pyairtable.Api.get`

1.2.0 (2022-07-09)
-------------------------

* Fixed missing rate limit in :meth:`~pyairtable.Api.batch_update` - `PR #162 <https://github.com/gtalarico/pyairtable/pull/162>`_.
* Added support for new parameter `return_fields_by_field_id` - `PR #161 <https://github.com/gtalarico/pyairtable/pull/161>`_. See updated :ref:`Parameters`.
* Added new ``OR`` formula - `PR #148 <https://github.com/gtalarico/pyairtable/pull/148>`_. See :mod:`pyairtable.formulas`.

1.1.0 (2022-02-21)
-------------------------

* Added support for ``cellFormat`` - `PR #140 <https://github.com/gtalarico/pyairtable/pull/140>`_.  See updated :ref:`Parameters`.


1.0.0 (2021-08-11)
-------------------------

* pyAirtable rewrite for 1.x - see :doc:`migrations`.

0.15.3 (2021-07-26)
-------------------------
