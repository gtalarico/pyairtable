.. |arg_base_id| replace:: An Airtable base id.

.. |arg_record_id| replace:: An Airtable record id.

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
    formula will be returned. For example, to only include records where
    ``COLUMN_A`` isn't empty, pass in ``formula="{COLUMN_A}"``.

.. |kwarg_typecast| replace:: The Airtable API will perform best-effort
    automatic data conversion from string values.

.. |kwarg_cell_format| replace:: The cell format to request from the Airtable
    API. Supported options are `json` (the default) and `string`.
    `json` will return cells as a JSON object. `string` will return
    the cell as a string. `user_locale` and `time_zone` must be set when using
    `string`.

.. |kwarg_user_locale| replace:: The user locale that should be used to format
    dates when using `string` as the `cell_format`. See
    https://support.airtable.com/hc/en-us/articles/220340268-Supported-locale-modifiers-for-SET-LOCALE
    for valid values.

.. |kwarg_time_zone| replace:: The time zone that should be used to format dates
    when using `string` as the `cell_format`. See
    https://support.airtable.com/hc/en-us/articles/216141558-Supported-timezones-for-SET-TIMEZONE
    for valid values.

.. |kwarg_replace| replace:: If ``True``, record is replaced in its entirety
    by provided fields; if a field is not included its value will
    bet set to null. If False, only provided fields are updated.

.. |kwarg_return_fields_by_field_id| replace:: An optional boolean value that lets you return field objects where the
    key is the field id. This defaults to `false`, which returns field objects where the key is the field name.
