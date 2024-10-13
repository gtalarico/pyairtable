.. |arg_base_id| replace:: An Airtable base ID.

.. |arg_record_id| replace:: An Airtable record ID.

.. |arg_table_id_or_name| replace:: An Airtable table ID or name.
        Table name should be unencoded, as shown on browser.

.. |kwarg_view| replace:: The name or ID of a view.
    If set, only the records in that view will be returned.
    The records will be sorted according to the order of the view.

.. |kwarg_page_size| replace:: The number of records returned
    in each request. Must be less than or equal to 100.
    If no value given, `Airtable's default <https://airtable.com/developers/web/api/list-records>`__ is 100.

.. |kwarg_max_records| replace:: The maximum total number of
    records that will be returned. If this value is larger than
    ``page_size``, multiple requests will be needed
    to fetch all records.

.. |kwarg_fields| replace:: Name of field or fields  to
    be retrieved. Default is all fields.
    Only data for fields whose names are in this list will be included in
    the records. If you don't need every field, you can use this parameter
    to reduce the amount of data transferred.

.. |kwarg_sort| replace:: List of fields to sort by.
    Default order is ascending.
    This parameter specifies how the records will be ordered. If you set the view
    parameter, the returned records in that view will be sorted by these
    fields. If sorting by multiple columns, column names can be passed as a list.
    Sorting Direction is ascending by default, but can be reversed by
    prefixing the column name with a minus sign ``-``.

.. |kwarg_formula| replace:: An Airtable formula. The formula will be evaluated for each record, and if the result
    is none of ``0``, ``false``, ``""``, ``NaN``, ``[]``, or ``#Error!`` the record will be included
    in the response. If combined with view, only records in that view which satisfy the
    formula will be returned. Read more at :doc:`formulas`.

.. |kwarg_typecast| replace:: The Airtable API will perform best-effort
    automatic data conversion from string values.

.. |kwarg_cell_format| replace:: The cell format to request from the Airtable
    API. Supported options are `json` (the default) and `string`.
    `json` will return cells as a JSON object. `string` will return
    the cell as a string. `user_locale` and `time_zone` must be set when using
    `string`.

.. |kwarg_user_locale| replace:: The user locale that should be used to format
    dates when using `string` as the `cell_format`. See
    `Supported SET_LOCALE modifiers <https://support.airtable.com/docs/supported-locale-modifiers-for-set-locale>`__
    for valid values.

.. |kwarg_time_zone| replace:: The time zone that should be used to format dates
    when using `string` as the `cell_format`. See
    `Supported SET_TIMEZONE timezones <https://support.airtable.com/docs/supported-timezones-for-set-timezone>`__
    for valid values.

.. |kwarg_replace| replace:: If ``True``, record is replaced in its entirety
    by provided fields; if a field is not included its value will
    bet set to null. If ``False``, only provided fields are updated.

.. |kwarg_use_field_ids| replace:: An optional boolean value that lets you return field objects where the
    key is the field id. This defaults to ``False``, which returns field objects where the key is the field name.
    This behavior can be overridden by passing ``use_field_ids=True`` to :class:`~pyairtable.Api`.

.. |kwarg_force_metadata| replace::
    By default, this method will only fetch information from the API if it has not been cached.
    If called with ``force=True`` it will always call the API, and will overwrite any cached values.

.. |kwarg_validate_metadata| replace::
    If ``False``, will create an object without validating the ID/name provided.
    If ``True``, will fetch information from the metadata API and validate the ID/name exists,
    raising ``KeyError`` if it does not.

.. |kwarg_orm_fetch| replace::
    If ``True``, records will be fetched and field values will be
    updated. If ``False``, new instances are created with the provided IDs,
    but field values are unset.

.. |kwarg_orm_memoize| replace::
    If ``True``, any objects created will be memoized for future reuse.
    If ``False``, objects created will *not* be memoized.
    The default behavior is defined on the :class:`~pyairtable.orm.Model` subclass.

.. |kwarg_orm_lazy| replace::
    If ``True``, this field will return empty objects with only IDs;
    call :meth:`~pyairtable.orm.Model.fetch` to retrieve values.

.. |kwarg_permission_level| replace::
    See `application permission levels <https://airtable.com/developers/web/api/model/application-permission-levels>`__.

.. |warn| unicode:: U+26A0 .. WARNING SIGN

.. |enterprise_only| replace:: |warn| This feature is only available on Enterprise billing plans.
