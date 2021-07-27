"""
This module provides functions to help you compose airtable formulas.


>>> table = Table("base_id", "Contact", "apiKey")
>>> formula = EQUAL("{First Name}", "'A'")
>>> table.get_all(formula=formula)


Text Column is not empty:

>>> airtable.get_all(formula="NOT({COLUMN_A}='')")

Text Column contains:

>>> airtable.get_all(formula="FIND('SomeSubText', {COLUMN_STR})=1")

"""
import re
from typing import Any


def quotes_escaped(value: str):
    """
    Ensures any quotes are escaped. Already escaped quotes are ignored.

    Args:
        value: text to be escaped

    Usage:
        >>> quotes_escaped("Player's Name")
        Player\'s Name
        >>> quotes_escaped("Player\'s Name")
        Player\'s Name
    """
    escaped_value = re.sub("(?<!\\\\)'", "\\'", value)
    return escaped_value


def to_airtable_value(value: Any):
    """
    Cast value to appropriate airtable types and format.

    Arg:
        value: value to be cast.

    * ``bool`` -> ``int``
    * ``str`` -> Text is wrapped in `'single quotes'`. Existing quotes are escaped.
    * ``float``, ``int`` -> no change
    """
    if isinstance(value, bool):
        return int(value)
    elif isinstance(value, (int, float)):
        return value
    elif isinstance(value, str):
        return STR_VALUE(quotes_escaped(value))
    else:
        return value


def fields_equals_values(dict_values):
    """
    Creates an ``AND()`` formula with equality expressions for each provided dict value

    Args:
        dict_values: dictionary containing column names and values

    Usage:
    >>> fields_equals_values({"First Name": "John", "Age": 21})
    "AND({First Name}='John',{Age}=21)"

    """
    expressions = []
    for key, value in dict_values.items():
        expression = EQUAL(FIELD(key), to_airtable_value(value))
        expressions.append(expression)

    formula = AND(*expressions)
    return formula


def field_equals_value(field_name, field_value):
    """
    Creates a formula to match cells from from field_name and value
    """

    cast_field_value = to_airtable_value(field_value)
    formula = EQUAL(FIELD(field_name), cast_field_value)
    return formula


def EQUAL(left: Any, right: Any) -> str:
    """
    Creates an equality assertion

    >>> EQUAL(2,2)
    '2=2'
    """
    return "{}={}".format(left, right)


def FIELD(name: str) -> str:
    """
    Creates a reference to a field

    Args:
        name: field name

    Usage:
        >>> FIELD("First Name"")
        '{First Name}'
    """
    return "{%s}" % name


def STR_VALUE(value: str) -> str:
    return "'{}'".format(value)


def IF(logical, value1, value2) -> str:
    """
    Creates an IF statement

    >>> IF("1=1"", 0, 1)
    'IF("1=1"", 0, 1)'
    """
    return "IF({}, {}, {})".format(logical, value1, value2)


def AND(*args) -> str:
    """
    Creates an AND Statement

    >>> AND(1, 2, 3)
    'AND(1, 2, 3)'
    """
    return "AND({})".format(",".join(args))


def FIND(find, where, start_from=None) -> str:
    ...
    # FIND(stringToFind, whereToSearch,[startFromPosition])
    # airtable.get_all(formula="FIND('SomeSubText', {COLUMN_STR})=1")
    # return "FIND('SomeSubText', {COLUMN_STR})=1"
