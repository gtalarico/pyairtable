=========
Changelog
=========

3.0 (TBD)
------------------------

* Rewrite of :mod:`pyairtable.formulas` module. See :ref:`Building Formulas`.
  - `PR #329 <https://github.com/gtalarico/pyairtable/pull/329>`_
* :class:`~pyairtable.orm.fields.TextField` and
  :class:`~pyairtable.orm.fields.CheckboxField` return ``""``
  or ``False`` instead of ``None``.
  - `PR #347 <https://github.com/gtalarico/pyairtable/pull/347>`_
* Changed the type of :data:`~pyairtable.orm.Model.created_time`
  from ``str`` to ``datetime``, along with all other timestamp fields
  used in :ref:`API: pyairtable.models`.
  - `PR #352 <https://github.com/gtalarico/pyairtable/pull/352>`_
* Added ORM field type :class:`~pyairtable.orm.fields.SingleLinkField`
  for record links that should only contain one record.
  - `PR #354 <https://github.com/gtalarico/pyairtable/pull/354>`_
* Support ``use_field_ids`` in the :ref:`ORM`.
  - `PR #355 <https://github.com/gtalarico/pyairtable/pull/355>`_
* Removed the ``pyairtable.metadata`` module.
  - `PR #360 <https://github.com/gtalarico/pyairtable/pull/360>`_
* Renamed ``return_fields_by_field_id=`` to ``use_field_ids=``.
  - `PR #362 <https://github.com/gtalarico/pyairtable/pull/362>`_
* Added ORM fields that :ref:`require a non-null value <Required Values>`.
  - `PR #363 <https://github.com/gtalarico/pyairtable/pull/363>`_
* Refactored methods for accessing ORM model configuration.
  - `PR #366 <https://github.com/gtalarico/pyairtable/pull/366>`_
* Added support for :ref:`memoization of ORM models <memoizing linked records>`.
  - `PR #369 <https://github.com/gtalarico/pyairtable/pull/369>`_
* Added `Enterprise.grant_access <pyairtable.Enterprise.grant_access>`
  and `Enterprise.revoke_access <pyairtable.Enterprise.revoke_access>`.
  - `PR #373 <https://github.com/gtalarico/pyairtable/pull/373>`_
* Added command line utility and ORM module generator. See :doc:`cli`.
  - `PR #376 <https://github.com/gtalarico/pyairtable/pull/376>`_
* Changed the behavior of :meth:`Model.save <pyairtable.orm.Model.save>`
  to no longer send unmodified field values to the API.
  - `PR #381 <https://github.com/gtalarico/pyairtable/pull/381>`_
* Added ``use_field_ids=`` parameter to :class:`~pyairtable.Api`.
  - `PR #386 <https://github.com/gtalarico/pyairtable/pull/386>`_
* Changed the return type of :meth:`Model.save <pyairtable.orm.Model.save>`
  from ``bool`` to :class:`~pyairtable.orm.SaveResult`.
  - `PR #387 <https://github.com/gtalarico/pyairtable/pull/387>`_
* Added support for `Upload attachment <https://airtable.com/developers/web/api/upload-attachment>`_
  via :meth:`Table.upload_attachment <pyairtable.Table.upload_attachment>`
  or :meth:`AttachmentsList.upload <pyairtable.orm.lists.AttachmentsList.upload>`.

2.3.3 (2024-03-22)
------------------------

* Fixed a bug affecting ORM Meta values which are computed at runtime.
  - `PR #357 <https://github.com/gtalarico/pyairtable/pull/357>`_.
* Fixed documentation for the ORM module.
  - `PR #356 <https://github.com/gtalarico/pyairtable/pull/356>`_.

2.3.2 (2024-03-18)
------------------------

* Fixed a bug affecting :func:`pyairtable.metadata.get_table_schema`.
  - `PR #349 <https://github.com/gtalarico/pyairtable/pull/349>`_.

2.3.1 (2024-03-14)
------------------------

* Fixed a bug affecting how timezones are parsed by :class:`~pyairtable.orm.fields.DatetimeField`.
  - `PR #342 <https://github.com/gtalarico/pyairtable/pull/342>`_.
* Fixed a bug affecting :meth:`~pyairtable.Base.create_table`.
  - `PR #345 <https://github.com/gtalarico/pyairtable/pull/345>`_.

2.3.0 (2024-02-25)
------------------------

* A breaking API change was accidentally introduced.
  Read more in :ref:`Migrating from 2.2 to 2.3`.
* Added support for :ref:`managing permissions and shares`
  and :ref:`managing users`.
  - `PR #337 <https://github.com/gtalarico/pyairtable/pull/337>`_.
* Added :meth:`Enterprise.audit_log <pyairtable.Enterprise.audit_log>`
  to iterate page-by-page through `audit log events <https://airtable.com/developers/web/api/audit-logs-overview>`__.
  - `PR #330 <https://github.com/gtalarico/pyairtable/pull/330>`_.
* :meth:`Api.base <pyairtable.Api.base>`,
  :meth:`Api.table <pyairtable.Api.table>`,
  and :meth:`Base.table <pyairtable.Base.table>`
  will use cached base metadata when called multiple times with ``validate=True``,
  unless the caller passes a new keyword argument ``force=True``.
  This allows callers to validate the IDs/names of many bases or tables at once
  without having to perform expensive network overhead each time.
  - `PR #336 <https://github.com/gtalarico/pyairtable/pull/336>`_.

2.2.2 (2024-01-28)
------------------------

* Enterprise methods :meth:`~pyairtable.Enterprise.user`,
  :meth:`~pyairtable.Enterprise.users`, and :meth:`~pyairtable.Enterprise.group`
  now return collaborations by default.
  - `PR #332 <https://github.com/gtalarico/pyairtable/pull/332>`_.
* Added more helper functions for formulas:
  :func:`~pyairtable.formulas.LESS`,
  :func:`~pyairtable.formulas.LESS_EQUAL`,
  :func:`~pyairtable.formulas.GREATER`,
  :func:`~pyairtable.formulas.GREATER_EQUAL`,
  and
  :func:`~pyairtable.formulas.NOT_EQUAL`.
  - `PR #323 <https://github.com/gtalarico/pyairtable/pull/323>`_.

2.2.1 (2023-11-28)
------------------------

* :meth:`~pyairtable.Table.update` now accepts ``return_fields_by_field_id=True``
  - `PR #320 <https://github.com/gtalarico/pyairtable/pull/320>`_.

2.2.0 (2023-11-13)
------------------------

* Fixed a bug in how webhook notification signatures are validated
  - `PR #312 <https://github.com/gtalarico/pyairtable/pull/312>`_.
* Added support for reading and modifying :doc:`metadata`
  - `PR #311 <https://github.com/gtalarico/pyairtable/pull/311>`_.
* Added support for the 'AI Text' field type
  - `PR #310 <https://github.com/gtalarico/pyairtable/pull/310>`_.
* Batch methods can now accept generators or iterators, not just lists
  - `PR #308 <https://github.com/gtalarico/pyairtable/pull/308>`_.
* Fixed a few documentation errors -
  `PR #301 <https://github.com/gtalarico/pyairtable/pull/301>`_,
  `PR #306 <https://github.com/gtalarico/pyairtable/pull/306>`_.

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
