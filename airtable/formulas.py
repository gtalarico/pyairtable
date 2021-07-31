import re
from typing import Any


def match(dict_values):
    """
    Creates one or more ``EQUAL()`` expressions for each provided dict value.
    If more than one assetions is included, the expressions are
    groupped together into using ``AND()``.

    This function also handles escaping field names and casting python values
    to the appropriate airtable types.

    Args:
        dict_values: dictionary containing column names and values

    Usage:
        >>> match({"First Name": "John", "Age": 21})
        "AND({First Name}='John',{Age}=21)"

    """
    expressions = []
    for key, value in dict_values.items():
        expression = EQUAL(FIELD(key), to_airtable_value(value))
        expressions.append(expression)

    if len(expressions) == 0:
        return ""
    elif len(expressions) == 1:
        return expressions[0]
    else:
        return AND(*expressions)


def quotes_escaped(value: str):
    r"""
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
