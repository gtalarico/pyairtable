"""
Formulas xxx

>>> table = Table(base_id, "Contact", os.environ["AIRTABLE_API_KEY"])
>>> formula = EQUAL("{First Name}", "'A'")
>>> table.get_all(formula=formula)

Others
******

Usage - Text Column is not empty:

>>> airtable.get_all(formula="NOT({COLUMN_A}='')")

Usage - Text Column contains:

>>> airtable.get_all(formula="FIND('SomeSubText', {COLUMN_STR})=1")

Args:
    formula (``str``): A valid Airtable formula.
"""
import re
from typing import Any


def quotes_escaped(value: str):
    """ensures any quotes are escaped"""
    escaped_value = re.sub("(?<!\\\\)'", "\\'", value)
    return escaped_value


def cast_value(value: Any):
    if isinstance(value, bool):
        return int(value)
    elif isinstance(value, (int, float)):
        return value
    elif isinstance(value, str):
        return STR_VALUE(quotes_escaped(value))
    else:
        return value


# WIP
def dict_query(dict_):
    """
    Usage:
    >>> query(name="John", age=21)

    """
    expressions = []
    for key, value in dict_.items():
        expression = EQUAL(FIELD(key), cast_value(value))
        expressions.append(expression)

    formula = AND(*expressions)
    return formula
    # assert formula == ("AND({First Name}='A',{Last Name}='B',{Age}='15')")


def field_equals_value(field_name, field_value):
    """
    Creates a formula to match cells from from field_name and value
    """

    cast_field_value = cast_value(field_value)
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
