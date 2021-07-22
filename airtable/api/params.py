"""
Parameter filters are instantiated internally
by using the corresponding keywords.

Filter names (kwargs) can be either the API camelCase name (ie ``maxRecords``)
or the snake-case equivalent (``max_records``).

Refer to the :any:`AirtableApi` class to verify which kwargs can be
used with each method.

The purpose of these classes is to 1. improve flexibility and
ways in which parameter filter values can be passed, and 2. properly format
the parameter names and values on the request url.

For more information see the full implementation below.

"""  #
from typing import List, Dict, Any
from textwrap import dedent
from collections import OrderedDict
import re


class InvalidParamException(ValueError):
    """Raise when invalid parameters are used"""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(message, *args)


def dict_list_to_request_params(param_name: str, values: List[dict]) -> dict:
    """
    Returns dict to be used by request params from dict list

    Expected Airtable Url Params is:
        `?sort[0][field]=FieldOne&sort[0][direction]=asc`

    >>> objects = [
    ...    { "field": "FieldOne", "direction": "asc"},
    ...    { "field": "FieldTwo", "direction": "desc"},
    ... ]
    >>> dict_list_to_request_params("sort", objects)
    {
        "sort[0][field]": "FieldOne",
        "sort[0][direction]: "asc",
        "sort[1][field]": "FieldTwo",
        "sort[1][direction]: "desc",
    }

    """
    param_dict = {}
    for index, dictionary in enumerate(values):
        for key, value in dictionary.items():
            field_name = "{param_name}[{index}][{key}]".format(
                param_name=param_name, index=index, key=key
            )
            param_dict[field_name] = value
    return OrderedDict(sorted(param_dict.items()))


def field_names_to_sorting_dict(field_names: List[str]) -> List[Dict[str, str]]:
    # TODO edge case fields starting with '-'
    """

    >>> field_names_to_sorting_dict(["Name", "-Age"])
    [
        { "field": "FieldOne", "direction": "asc"},
        { "field": "FieldTwo", "direction": "desc"},
    ]
    """
    values = []

    for field_name in field_names:

        if field_name.startswith("-"):
            direction = "desc"
            field_name = field_name[1:]
        else:
            direction = "asc"

        sort_param = {"field": field_name, "direction": direction}
        values.append(sort_param)
    return values


def to_params_dict(param_name: str, value: Any):
    """Returns a dictionary for use in Request 'params'"""
    if param_name == "max_records":
        return {"maxRecords": value}
    elif param_name == "view":
        return {"view": value}
    elif param_name == "page_size":
        return {"pageSize": value}
    elif param_name == "offset":
        return {"offset": value}
    elif param_name == "formula":
        return {"filterByFormula": value}
    elif param_name == "fields":
        return {"fields[]": value}
    elif param_name == "sort":
        sorting_dict_list = field_names_to_sorting_dict(value)
        return dict_list_to_request_params("sort", sorting_dict_list)
    else:
        msg = "'{0}' is not a supported parameter".format(param_name)
        raise InvalidParamException(msg)


doc_strings = dict(
    # Library,
    record_id=dedent(
        """\
        record_id(``str``): Airtable record id
    """
    ),
    table_name=dedent(
        """\
        table_name(``str``): Airtable table name. Value will be url encoded, so
                use value as shown in Airtable.
    """
    ),
    # Official,, Public
    max_records=dedent(
        """\
        max_records (``int``, optional): The maximum total number of
            records that will be returned.
    """
    ),
    view=dedent(
        """\
        view (``str``, optional): The name or ID of a view.
            If set, only the records in that view will be returned.
            The records will be sorted according to the order of the view.
    """
    ),
    page_size=dedent(
        """\
        page_size (``int``, optional ): The number of records returned
            in each request. Must be less than or equal to 100.
            Default is 100.
    """
    ),
    fields=dedent(
        """\
        fields (``str``, ``list``, optional): Name of field or fields  to
            be retrieved. Default is all fields.
            Only data for fields whose names are in this list will be included in
            the records. If you don't need every field, you can use this parameter
            to reduce the amount of data transferred.
    """
    ),
    sort=dedent(
        """\
        sort (``list``, optional): List of fields to sort by.
            Default order is ascending.
            This parameter specifies how the records will be ordered. If you set the view
            parameter, the returned records in that view will be sorted by these
            fields.

            If sorting by multiple columns, column names can be passed as a list.
            Sorting Direction is ascending by default, but can be reversed by
            prefixing the column name with a minus sign ``-``.
    """
    ),
    formula=dedent(
        """\
        formula (``str``, optional): An Airtable formula.
            The formula will be evaluated for each record, and if the result
            is not 0, false, "", NaN, [], or #Error! the record will be included
            in the response.

            If combined with view, only records in that view which satisfy the
            formula will be returned. For example, to only include records where
            ``COLUMN_A`` isn't empty, pass in: ``"NOT({COLUMN_A}='')"``

            For more information see
                `Airtable Docs on formulas. <https://airtable.com/api>`_
    """
    ),
    typescast=dedent(
        """\
        typecast(``boolean``): Automatic data conversion from string values.
    """
    )
    # Others
    # offset: str
    # records[]: str
)
