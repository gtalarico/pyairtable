"""
Formulas xxx

>>> table = Table(base_id, "Contact", os.environ["AIRTABLE_API_KEY"])
>>> formula = EQUAL("{First Name}", "'A'")
>>> table.get_all(formula=formula)
>>> formula = AND(
...     EQUAL(FIELD("First Name"), STR_VALUE("A")),
...     EQUAL(FIELD("Last Name"), STR_VALUE("Talarico")),
...     EQUAL(FIELD("Age"), STR_VALUE(15)),
... )
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


def field_equals_value(field_name, field_value):
    """
    Creates a formula to match cells from from field_name and value
    """
    if isinstance(field_value, str):
        field_value = STR_VALUE(field_value)

    formula = EQUAL(FIELD(field_name), field_value)
    return formula


def EQUAL(left: str, right: str) -> str:
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
    return "'%s'" % value


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
