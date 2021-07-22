

.. |arg_base_id| replace:: Airtable base id.

.. |arg_record_id| replace:: An Airtable record id.

.. |arg_table_name| replace:: Airtable table name. Table name should be unencoded,
                as shown on browser.

.. |kwarg_view| replace:: The name or ID of a view.
    If set, only the records in that view will be returned.
    The records will be sorted according to the order of the view.

.. |kwarg_page_size| replace:: The number of records returned
    in each request. Must be less than or equal to 100.
    Default is 100.

.. |kwarg_max_records| replace:: The maximum total number of
    records that will be returned.

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
    is not 0, false, "", NaN, [], or #Error! the record will be included
    in the response. If combined with view, only records in that view which satisfy the
    formula will be returned. For example, to only include records where
    ``COLUMN_A`` isn't empty, pass in: ``"NOT({COLUMN_A}='')"``.
