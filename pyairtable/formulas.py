"""
This module exports building blocks for constructing Airtable formulas,
including function call proxies for all formula functions as of Dec '23.

See :doc:`formulas` for more information.
"""

import datetime
import re
import warnings
from decimal import Decimal
from fractions import Fraction
from typing import Any, ClassVar, Iterable, List, Optional, Set, Union

from typing_extensions import Self as SelfType
from typing_extensions import TypeAlias

from pyairtable.api.types import Fields
from pyairtable.exceptions import CircularFormulaError
from pyairtable.utils import date_to_iso_str, datetime_to_iso_str


class Formula:
    """
    Represents an Airtable formula that can be combined with other formulas
    or converted to a string. On its own, this class simply wraps a ``str``
    so that it will be not be modified or escaped as if it were a value.

    >>> Formula("{Column} = 1")
    Formula('{Column} = 1')
    >>> str(_)
    '{Column} = 1'
    """

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"

    def __and__(self, other: Any) -> "Formula":
        return AND(self, to_formula(other))

    def __or__(self, other: Any) -> "Formula":
        return OR(self, to_formula(other))

    def __xor__(self, other: Any) -> "Formula":
        return XOR(self, to_formula(other))

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return False
        return other.value == self.value

    def __invert__(self) -> "Formula":
        return NOT(self)

    def flatten(self) -> "Formula":
        """
        Return a new formula with nested boolean statements flattened.
        """
        return self

    def eq(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.EQ` comparison using this formula.
        """
        return EQ(self, value)

    def ne(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.NE` comparison using this formula.
        """
        return NE(self, value)

    def gt(self, value: Any) -> "Comparison":
        """
        Build a :class:`~pyairtable.formulas.GT` comparison using this formula.
        """
        return GT(self, value)

    def lt(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.LT` comparison using this formula.
        """
        return LT(self, value)

    def gte(self, value: Any) -> "Comparison":
        """
        Build a :class:`~pyairtable.formulas.GTE` comparison using this formula.
        """
        return GTE(self, value)

    def lte(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.LTE` comparison using this formula.
        """
        return LTE(self, value)


class Field(Formula):
    """
    Represents a field name.
    """

    def __str__(self) -> str:
        return field_name(self.value)


class Comparison(Formula):
    """
    Represents a logical condition that compares two expressions.
    """

    operator: ClassVar[str] = ""

    def __init__(self, lval: Any, rval: Any):
        if not self.operator:
            raise NotImplementedError(
                f"{self.__class__.__name__}.operator is not defined"
            )
        self.lval = lval
        self.rval = rval

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Comparison):
            return False
        return (self.lval, self.operator, self.rval) == (
            other.lval,
            other.operator,
            other.rval,
        )

    def __str__(self) -> str:
        lval, rval = (to_formula_str(v) for v in (self.lval, self.rval))
        lval = f"({lval})" if isinstance(self.lval, Comparison) else lval
        rval = f"({rval})" if isinstance(self.rval, Comparison) else rval
        return f"{lval}{self.operator}{rval}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.lval!r}, {self.rval!r})"


class EQ(Comparison):
    """
    Produces an ``lval = rval`` formula.
    """

    operator = "="


class NE(Comparison):
    """
    Produces an ``lval != rval`` formula.
    """

    operator = "!="


class GT(Comparison):
    """
    Produces an ``lval > rval`` formula.
    """

    operator = ">"


class GTE(Comparison):
    """
    Produces an ``lval >= rval`` formula.
    """

    operator = ">="


class LT(Comparison):
    """
    Produces an ``lval < rval`` formula.
    """

    operator = "<"


class LTE(Comparison):
    """
    Produces an ``lval <= rval`` formula.
    """

    operator = "<="


COMPARISONS_BY_OPERATOR = {cls.operator: cls for cls in (EQ, NE, GT, GTE, LT, LTE)}


class Compound(Formula):
    """
    Represents a boolean logical operator (AND, OR, etc.) wrapping around
    one or more component formulas.
    """

    operator: str
    components: List[Formula]

    def __init__(
        self,
        operator: str,
        components: Iterable[Formula],
    ) -> None:
        if not isinstance(components, list):
            components = list(components)
        if len(components) == 0:
            raise ValueError("Compound() requires at least one component")

        self.operator = operator
        self.components = components

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Compound):
            return False
        return (self.operator, self.components) == (other.operator, other.components)

    def __str__(self) -> str:
        joined_components = ", ".join(str(c) for c in self.components)
        return f"{self.operator}({joined_components})"

    def __repr__(self) -> str:
        return f"{self.operator}({repr(self.components)[1:-1]})"

    def flatten(self, /, memo: Optional[Set[int]] = None) -> "Compound":
        """
        Reduces the depth of nested AND, OR, and NOT statements.
        """
        memo = memo if memo else set()
        memo.add(id(self))
        flattened: List[Formula] = []
        for item in self.components:
            if id(item) in memo:
                raise CircularFormulaError(item)
            if isinstance(item, Compound) and item.operator == self.operator:
                flattened.extend(item.flatten(memo=memo).components)
            else:
                flattened.append(item.flatten())

        return Compound(self.operator, flattened)

    @classmethod
    def build(cls, operator: str, *components: Any, **fields: Any) -> SelfType:
        items = list(components)
        if len(items) == 1 and hasattr(first := items[0], "__iter__"):
            items = [first] if isinstance(first, str) else list(first)
        if fields:
            items.extend(EQ(Field(k), v) for (k, v) in fields.items())
        return cls(operator, items)


def AND(*components: Union[Formula, Iterable[Formula]], **fields: Any) -> Compound:
    """
    Join one or more logical conditions into an AND compound condition.
    Keyword arguments will be treated as field names.

    >>> AND(EQ("foo", 1), EQ(Field("bar"), 2), baz=3)
    AND(EQ('foo', 1), EQ(Field('bar'), 2), EQ(Field('baz'), 3))
    """
    return Compound.build("AND", *components, **fields)


def OR(*components: Union[Formula, Iterable[Formula]], **fields: Any) -> Compound:
    """
    Join one or more logical conditions into an OR compound condition.
    Keyword arguments will be treated as field names.

    >>> OR(EQ("foo", 1), EQ(Field("bar"), 2), baz=3)
    OR(EQ('foo', 1), EQ(Field('bar'), 2), EQ(Field('baz'), 3))
    """
    return Compound.build("OR", *components, **fields)


def NOT(component: Optional[Formula] = None, /, **fields: Any) -> Compound:
    """
    Wrap one logical condition in a negation compound.
    Keyword arguments will be treated as field names.

    Can be called with either a formula or with a single
    kewyord argument, but not both.

    >>> NOT(EQ("foo", 1))
    NOT(EQ('foo', 1))

    >>> NOT(foo=1)
    NOT(EQ(Field('foo'), 1))

    If not called with exactly one condition, will throw an exception:

    >>> NOT(EQ("foo", 1), EQ("bar", 2))
    Traceback (most recent call last):
    TypeError: NOT() takes from 0 to 1 positional arguments but 2 were given

    >>> NOT(EQ("foo", 1), bar=2)
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 2

    >>> NOT(foo=1, bar=2)
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 2

    >>> NOT()
    Traceback (most recent call last):
    ValueError: NOT() requires exactly one condition; got 0
    """
    items: List[Formula] = [EQ(Field(k), v) for (k, v) in fields.items()]
    if component:
        items.append(component)
    if (count := len(items)) != 1:
        raise ValueError(f"NOT() requires exactly one condition; got {count}")
    return Compound.build("NOT", items)


def match(field_values: Fields, *, match_any: bool = False) -> Formula:
    r"""
    Create one or more equality expressions for each provided value,
    treating keys as field names and values as values (not formula expressions).

    If more than one assertion is included, the expressions are
    grouped together into using ``AND()`` (all values must match).
    If ``match_any=True``, expressions are grouped with ``OR()``.

        >>> match({"First Name": "John", "Age": 21})
        AND(EQ(Field('First Name'), 'John'),
            EQ(Field('Age'), 21))

        >>> match({"First Name": "John", "Age": 21}, match_any=True)
        OR(EQ(Field('First Name'), 'John'),
           EQ(Field('Age'), 21))

    To use comparisons other than equality, use a 2-tuple of ``(operator, value)``
    as the value for a particular field. For example:

        >>> match({"First Name": "John", "Age": (">=", 21)})
        AND(EQ(Field('First Name'), 'John'),
            GTE(Field('Age'), 21))

    If you need more advanced matching you can build formula expressions using lower
    level primitives.

    Args:
        field_values: mapping of column names to values
            (or to 2-tuples of the format ``(operator, value)``).
        match_any:
            If ``True``, matches if *any* of the provided values match.
            Otherwise, all values must match.
    """
    expressions: List[Formula] = []

    for key, val in field_values.items():
        if isinstance(val, tuple) and len(val) == 2:
            cmp, val = COMPARISONS_BY_OPERATOR[val[0]], val[1]
        else:
            cmp = EQ
        expressions.append(cmp(Field(key), val))

    if len(expressions) == 0:
        raise ValueError(
            "match() requires at least one field-value pair or keyword argument"
        )
    if len(expressions) == 1:
        return expressions[0]
    if match_any:
        return OR(*expressions)
    return AND(*expressions)


def to_formula(value: Any) -> Formula:
    """
    Converts the given value into a Formula object.

    When given a Formula object, it returns the object as-is:

    >>> to_formula(EQ(F.Formula("a"), "b"))
    EQ(Formula('a'), 'b')

    When given a scalar value, it simply wraps that value's string representation
    in a Formula object:

    >>> to_formula(1)
    Formula('1')
    >>> to_formula('foo')
    Formula("'foo'")

    Boolean and date values receive custom function calls:

    >>> to_formula(True)
    TRUE()
    >>> to_formula(False)
    FALSE()
    >>> to_formula(datetime.date(2023, 12, 1))
    DATETIME_PARSE('2023-12-01')
    >>> to_formula(datetime.datetime(2023, 12, 1, 12, 34, 56))
    DATETIME_PARSE('2023-12-01T12:34:56.000Z')
    """
    if isinstance(value, Formula):
        return value
    if isinstance(value, bool):
        return TRUE() if value else FALSE()
    if isinstance(value, (int, float, Decimal, Fraction)):
        return Formula(str(value))
    if isinstance(value, str):
        return Formula(quoted(value))
    if isinstance(value, datetime.datetime):
        return DATETIME_PARSE(datetime_to_iso_str(value))
    if isinstance(value, datetime.date):
        return DATETIME_PARSE(date_to_iso_str(value))

    # Runtime import to avoid circular dependency
    import pyairtable.orm

    if isinstance(value, pyairtable.orm.fields.Field):
        return Field(value.field_name)

    raise TypeError(value, type(value))


def to_formula_str(value: Any) -> str:
    """
    Converts the given value into a string representation that can be used
    in an Airtable formula expression.

    >>> to_formula_str(EQ(F.Formula("a"), "b"))
    "a='b'"
    >>> to_formula_str(True)
    'TRUE()'
    >>> to_formula_str(False)
    'FALSE()'
    >>> to_formula_str(3)
    '3'
    >>> to_formula_str(3.5)
    '3.5'
    >>> to_formula_str(Decimal("3.14159265"))
    '3.14159265'
    >>> to_formula_str(Fraction("4/19"))
    '4/19'
    >>> to_formula_str("asdf")
    "'asdf'"
    >>> to_formula_str("Jane's")
    "'Jane\\'s'"
    >>> to_formula_str(datetime.date(2023, 12, 1))
    "DATETIME_PARSE('2023-12-01')"
    >>> to_formula_str(datetime.datetime(2023, 12, 1, 12, 34, 56))
    "DATETIME_PARSE('2023-12-01T12:34:56.000Z')"
    """
    return str(to_formula(value))


def quoted(value: str) -> str:
    r"""
    Wrap string in quotes. This is needed when referencing a string inside a formula.
    Quotes are escaped.

    >>> quoted("John")
    "'John'"
    >>> quoted("Guest's Name")
    "'Guest\\'s Name'"
    """
    value = value.replace("\\", r"\\").replace("'", r"\'")
    return "'{}'".format(value)


def escape_quotes(value: str) -> str:  # pragma: no cover
    r"""
    Ensure any quotes are escaped. Already escaped quotes are ignored.

    This function has been deprecated.
    Use :func:`~pyairtable.formulas.quoted` instead.

    Args:
        value: text to be escaped

    Usage:
        >>> escape_quotes(r"Player's Name")
        "Player\\'s Name"
        >>> escape_quotes(r"Player\'s Name")
        "Player\\'s Name"
    """
    warnings.warn(
        "escape_quotes is deprecated; use quoted() instead.",
        category=DeprecationWarning,
        stacklevel=2,
    )
    escaped_value = re.sub("(?<!\\\\)'", "\\'", value)
    return escaped_value


def field_name(name: str) -> str:
    r"""
    Create a reference to a field. Quotes are escaped.

    Args:
        name: field name

    Usage:
        >>> field_name("First Name")
        '{First Name}'
        >>> field_name("Guest's Name")
        "{Guest's Name}"
    """
    # This will not actually work with field names that contain more
    # than one closing curly brace; that's a limitation of Airtable.
    # Our library will escape all closing braces, but the API will fail.
    return "{%s}" % name.replace("}", r"\}")


FunctionArg: TypeAlias = Union[
    str,
    int,
    float,
    bool,
    Decimal,
    Fraction,
    Formula,
    datetime.date,
    datetime.datetime,
]


class FunctionCall(Formula):
    """
    Represents a function call in an Airtable formula, and converts
    all arguments to that function into Airtable formula expressions.

    >>> FunctionCall("WEEKDAY", datetime.date(2024, 1, 1))
    WEEKDAY(datetime.date(2024, 1, 1))
    >>> str(_)
    "WEEKDAY(DATETIME_PARSE('2024-01-01'))"

    pyAirtable exports shortcuts like :meth:`~pyairtable.formulas.WEEKDAY`
    for all formula functions known at time of publishing.
    """

    def __init__(self, name: str, *args: FunctionArg):
        self.name = name
        self.args = args

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, FunctionCall):
            return False
        return (self.name, self.args) == (other.name, other.args)

    def __str__(self) -> str:
        joined_args = ", ".join(to_formula_str(v) for v in self.args)
        return f"{self.name}({joined_args})"

    def __repr__(self) -> str:
        joined_args_repr = ", ".join(repr(v) for v in self.args)
        return f"{self.name}({joined_args_repr})"


# fmt: off
r"""[[[cog]]]

import re
from pathlib import Path

definitions = [
    line.strip()
    for line in Path(cog.inFile).with_suffix(".txt").read_text().splitlines()
    if line.strip()
    and not line.startswith("#")
]

cog.outl("\n")

for definition in definitions:
    comment = ""
    if "#" in definition:
        definition, comment = (x.strip() for x in definition.split("#", 1))

    name, argspec = definition.rstrip(")").split("(", 1)
    if name in ("AND", "OR", "NOT"):
        continue

    args = [
        re.sub(
            "([a-z])([A-Z])",
            lambda m: m[1] + "_" + m[2].lower(),
            name.strip()
        )
        for name in argspec.split(",")
    ]

    required = [arg for arg in args if arg and not arg.startswith("[")]
    optional = [arg.strip("[]") for arg in args if arg.startswith("[") and arg.endswith("]")]
    signature = [f"{arg}: FunctionArg" for arg in required]
    params = [*required]
    splat = optional.pop().rstrip(".") if optional and optional[-1].endswith("...") else None

    if optional:
        signature += [f"{arg}: Optional[FunctionArg] = None" for arg in optional]
        params += ["*(v for v in [" + ", ".join(optional) + "] if v is not None)"]

    if required or optional:
        signature += ["/"]

    if splat:
        signature += [f"*{splat}: FunctionArg"]
        params += [f"*{splat}"]

    joined_signature = ", ".join(signature)
    joined_params = (", " + ", ".join(params)) if params else ""

    cog.outl(f"def {name}({joined_signature}) -> FunctionCall:")
    cog.outl(f"    \"\"\"")
    if comment:
        cog.outl(f"    {comment}")
    else:
        cog.outl(f"    Produce a formula that calls ``{name}()``")
    cog.outl(f"    \"\"\"")
    cog.outl(f"    return FunctionCall({name!r}{joined_params})")
    cog.outl("\n")

[[[out]]]"""


def ABS(value: FunctionArg, /) -> FunctionCall:
    """
    Returns the absolute value.
    """
    return FunctionCall('ABS', value)


def AVERAGE(number: FunctionArg, /, *numbers: FunctionArg) -> FunctionCall:
    """
    Returns the average of the numbers.
    """
    return FunctionCall('AVERAGE', number, *numbers)


def BLANK() -> FunctionCall:
    """
    Returns a blank value.
    """
    return FunctionCall('BLANK')


def CEILING(value: FunctionArg, significance: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Returns the nearest integer multiple of significance that is greater than or equal to the value. If no significance is provided, a significance of 1 is assumed.
    """
    return FunctionCall('CEILING', value, *(v for v in [significance] if v is not None))


def CONCATENATE(text: FunctionArg, /, *texts: FunctionArg) -> FunctionCall:
    """
    Joins together the text arguments into a single text value.
    """
    return FunctionCall('CONCATENATE', text, *texts)


def COUNT(number: FunctionArg, /, *numbers: FunctionArg) -> FunctionCall:
    """
    Count the number of numeric items.
    """
    return FunctionCall('COUNT', number, *numbers)


def COUNTA(value: FunctionArg, /, *values: FunctionArg) -> FunctionCall:
    """
    Count the number of non-empty values. This function counts both numeric and text values.
    """
    return FunctionCall('COUNTA', value, *values)


def COUNTALL(value: FunctionArg, /, *values: FunctionArg) -> FunctionCall:
    """
    Count the number of all elements including text and blanks.
    """
    return FunctionCall('COUNTALL', value, *values)


def CREATED_TIME() -> FunctionCall:
    """
    Returns the date and time a given record was created.
    """
    return FunctionCall('CREATED_TIME')


def DATEADD(date: FunctionArg, number: FunctionArg, units: FunctionArg, /) -> FunctionCall:
    """
    Adds specified "count" units to a datetime. (See `list of shared unit specifiers <https://support.airtable.com/hc/en-us/articles/226061308>`__. For this function we recommend using the full unit specifier for your desired unit.)
    """
    return FunctionCall('DATEADD', date, number, units)


def DATESTR(date: FunctionArg, /) -> FunctionCall:
    """
    Formats a datetime into a string (YYYY-MM-DD).
    """
    return FunctionCall('DATESTR', date)


def DATETIME_DIFF(date1: FunctionArg, date2: FunctionArg, units: FunctionArg, /) -> FunctionCall:
    """
    Returns the difference between datetimes in specified units. The difference between datetimes is determined by subtracting [date2] from [date1]. This means that if [date2] is later than [date1], the resulting value will be negative.
    """
    return FunctionCall('DATETIME_DIFF', date1, date2, units)


def DATETIME_FORMAT(date: FunctionArg, output_format: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Formats a datetime into a specified string. See an `explanation of how to use this function with date fields <https://support.airtable.com/hc/en-us/articles/215646218>`__ or a list of `supported format specifiers <https://support.airtable.com/hc/en-us/articles/216141218>`__.
    """
    return FunctionCall('DATETIME_FORMAT', date, *(v for v in [output_format] if v is not None))


def DATETIME_PARSE(date: FunctionArg, input_format: Optional[FunctionArg] = None, locale: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Interprets a text string as a structured date, with optional input format and locale parameters. The output format will always be formatted 'M/D/YYYY h:mm a'.
    """
    return FunctionCall('DATETIME_PARSE', date, *(v for v in [input_format, locale] if v is not None))


def DAY(date: FunctionArg, /) -> FunctionCall:
    """
    Returns the day of the month of a datetime in the form of a number between 1-31.
    """
    return FunctionCall('DAY', date)


def ENCODE_URL_COMPONENT(component_string: FunctionArg, /) -> FunctionCall:
    """
    Replaces certain characters with encoded equivalents for use in constructing URLs or URIs. Does not encode the following characters: ``-_.~``
    """
    return FunctionCall('ENCODE_URL_COMPONENT', component_string)


def ERROR() -> FunctionCall:
    """
    Returns a generic Error value (``#ERROR!``).
    """
    return FunctionCall('ERROR')


def EVEN(value: FunctionArg, /) -> FunctionCall:
    """
    Returns the smallest even integer that is greater than or equal to the specified value.
    """
    return FunctionCall('EVEN', value)


def EXP(power: FunctionArg, /) -> FunctionCall:
    """
    Computes **Euler's number** (e) to the specified power.
    """
    return FunctionCall('EXP', power)


def FALSE() -> FunctionCall:
    """
    Logical value false. False is represented numerically by a 0.
    """
    return FunctionCall('FALSE')


def FIND(string_to_find: FunctionArg, where_to_search: FunctionArg, start_from_position: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Finds an occurrence of stringToFind in whereToSearch string starting from an optional startFromPosition.(startFromPosition is 0 by default.) If no occurrence of stringToFind is found, the result will be 0.
    """
    return FunctionCall('FIND', string_to_find, where_to_search, *(v for v in [start_from_position] if v is not None))


def FLOOR(value: FunctionArg, significance: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Returns the nearest integer multiple of significance that is less than or equal to the value. If no significance is provided, a significance of 1 is assumed.
    """
    return FunctionCall('FLOOR', value, *(v for v in [significance] if v is not None))


def FROMNOW(date: FunctionArg, /) -> FunctionCall:
    """
    Calculates the number of days between the current date and another date.
    """
    return FunctionCall('FROMNOW', date)


def HOUR(datetime: FunctionArg, /) -> FunctionCall:
    """
    Returns the hour of a datetime as a number between 0 (12:00am) and 23 (11:00pm).
    """
    return FunctionCall('HOUR', datetime)


def IF(expression: FunctionArg, if_true: FunctionArg, if_false: FunctionArg, /) -> FunctionCall:
    """
    Returns value1 if the logical argument is true, otherwise it returns value2. Can also be used to make `nested IF statements <https://support.airtable.com/hc/en-us/articles/221564887-Nested-IF-formulas>`__.
    """
    return FunctionCall('IF', expression, if_true, if_false)


def INT(value: FunctionArg, /) -> FunctionCall:
    """
    Returns the greatest integer that is less than or equal to the specified value.
    """
    return FunctionCall('INT', value)


def ISERROR(expr: FunctionArg, /) -> FunctionCall:
    """
    Returns true if the expression causes an error.
    """
    return FunctionCall('ISERROR', expr)


def IS_AFTER(date1: FunctionArg, date2: FunctionArg, /) -> FunctionCall:
    """
    Determines if [date1] is later than [date2]. Returns 1 if yes, 0 if no.
    """
    return FunctionCall('IS_AFTER', date1, date2)


def IS_BEFORE(date1: FunctionArg, date2: FunctionArg, /) -> FunctionCall:
    """
    Determines if [date1] is earlier than [date2]. Returns 1 if yes, 0 if no.
    """
    return FunctionCall('IS_BEFORE', date1, date2)


def IS_SAME(date1: FunctionArg, date2: FunctionArg, unit: FunctionArg, /) -> FunctionCall:
    """
    Compares two dates up to a unit and determines whether they are identical. Returns 1 if yes, 0 if no.
    """
    return FunctionCall('IS_SAME', date1, date2, unit)


def LAST_MODIFIED_TIME(*fields: FunctionArg) -> FunctionCall:
    """
    Returns the date and time of the most recent modification made by a user in a non-computed field in the table.
    """
    return FunctionCall('LAST_MODIFIED_TIME', *fields)


def LEFT(string: FunctionArg, how_many: FunctionArg, /) -> FunctionCall:
    """
    Extract how many characters from the beginning of the string.
    """
    return FunctionCall('LEFT', string, how_many)


def LEN(string: FunctionArg, /) -> FunctionCall:
    """
    Returns the length of a string.
    """
    return FunctionCall('LEN', string)


def LOG(number: FunctionArg, base: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Computes the logarithm of the value in provided base. The base defaults to 10 if not specified.
    """
    return FunctionCall('LOG', number, *(v for v in [base] if v is not None))


def LOWER(string: FunctionArg, /) -> FunctionCall:
    """
    Makes a string lowercase.
    """
    return FunctionCall('LOWER', string)


def MAX(number: FunctionArg, /, *numbers: FunctionArg) -> FunctionCall:
    """
    Returns the largest of the given numbers.
    """
    return FunctionCall('MAX', number, *numbers)


def MID(string: FunctionArg, where_to_start: FunctionArg, count: FunctionArg, /) -> FunctionCall:
    """
    Extract a substring of count characters starting at whereToStart.
    """
    return FunctionCall('MID', string, where_to_start, count)


def MIN(number: FunctionArg, /, *numbers: FunctionArg) -> FunctionCall:
    """
    Returns the smallest of the given numbers.
    """
    return FunctionCall('MIN', number, *numbers)


def MINUTE(datetime: FunctionArg, /) -> FunctionCall:
    """
    Returns the minute of a datetime as an integer between 0 and 59.
    """
    return FunctionCall('MINUTE', datetime)


def MOD(value: FunctionArg, divisor: FunctionArg, /) -> FunctionCall:
    """
    Returns the remainder after dividing the first argument by the second.
    """
    return FunctionCall('MOD', value, divisor)


def MONTH(date: FunctionArg, /) -> FunctionCall:
    """
    Returns the month of a datetime as a number between 1 (January) and 12 (December).
    """
    return FunctionCall('MONTH', date)


def NOW() -> FunctionCall:
    """
    While similar to the TODAY() function, NOW() returns the current date AND time.
    """
    return FunctionCall('NOW')


def ODD(value: FunctionArg, /) -> FunctionCall:
    """
    Rounds positive value up the the nearest odd number and negative value down to the nearest odd number.
    """
    return FunctionCall('ODD', value)


def POWER(base: FunctionArg, power: FunctionArg, /) -> FunctionCall:
    """
    Computes the specified base to the specified power.
    """
    return FunctionCall('POWER', base, power)


def RECORD_ID() -> FunctionCall:
    """
    Returns the ID of the current record.
    """
    return FunctionCall('RECORD_ID')


def REGEX_EXTRACT(string: FunctionArg, regex: FunctionArg, /) -> FunctionCall:
    """
    Returns the first substring that matches a regular expression.
    """
    return FunctionCall('REGEX_EXTRACT', string, regex)


def REGEX_MATCH(string: FunctionArg, regex: FunctionArg, /) -> FunctionCall:
    """
    Returns whether the input text matches a regular expression.
    """
    return FunctionCall('REGEX_MATCH', string, regex)


def REGEX_REPLACE(string: FunctionArg, regex: FunctionArg, replacement: FunctionArg, /) -> FunctionCall:
    """
    Substitutes all matching substrings with a replacement string value.
    """
    return FunctionCall('REGEX_REPLACE', string, regex, replacement)


def REPLACE(string: FunctionArg, start_character: FunctionArg, number_of_characters: FunctionArg, replacement: FunctionArg, /) -> FunctionCall:
    """
    Replaces the number of characters beginning with the start character with the replacement text.
    """
    return FunctionCall('REPLACE', string, start_character, number_of_characters, replacement)


def REPT(string: FunctionArg, number: FunctionArg, /) -> FunctionCall:
    """
    Repeats string by the specified number of times.
    """
    return FunctionCall('REPT', string, number)


def RIGHT(string: FunctionArg, how_many: FunctionArg, /) -> FunctionCall:
    """
    Extract howMany characters from the end of the string.
    """
    return FunctionCall('RIGHT', string, how_many)


def ROUND(value: FunctionArg, precision: FunctionArg, /) -> FunctionCall:
    """
    Rounds the value to the number of decimal places given by "precision." (Specifically, ROUND will round to the nearest integer at the specified precision, with ties broken by `rounding half up toward positive infinity <https://en.wikipedia.org/wiki/Rounding#Round_half_up>`__.)
    """
    return FunctionCall('ROUND', value, precision)


def ROUNDDOWN(value: FunctionArg, precision: FunctionArg, /) -> FunctionCall:
    """
    Rounds the value to the number of decimal places given by "precision," always `rounding down <https://en.wikipedia.org/wiki/Rounding#Rounding_to_integer>`__.
    """
    return FunctionCall('ROUNDDOWN', value, precision)


def ROUNDUP(value: FunctionArg, precision: FunctionArg, /) -> FunctionCall:
    """
    Rounds the value to the number of decimal places given by "precision," always `rounding up <https://en.wikipedia.org/wiki/Rounding#Rounding_to_integer>`__.
    """
    return FunctionCall('ROUNDUP', value, precision)


def SEARCH(string_to_find: FunctionArg, where_to_search: FunctionArg, start_from_position: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Searches for an occurrence of stringToFind in whereToSearch string starting from an optional startFromPosition. (startFromPosition is 0 by default.) If no occurrence of stringToFind is found, the result will be empty.
    """
    return FunctionCall('SEARCH', string_to_find, where_to_search, *(v for v in [start_from_position] if v is not None))


def SECOND(datetime: FunctionArg, /) -> FunctionCall:
    """
    Returns the second of a datetime as an integer between 0 and 59.
    """
    return FunctionCall('SECOND', datetime)


def SET_LOCALE(date: FunctionArg, locale_modifier: FunctionArg, /) -> FunctionCall:
    """
    Sets a specific locale for a datetime. **Must be used in conjunction with DATETIME_FORMAT.** A list of supported locale modifiers can be found `here <https://support.airtable.com/hc/en-us/articles/220340268>`__.
    """
    return FunctionCall('SET_LOCALE', date, locale_modifier)


def SET_TIMEZONE(date: FunctionArg, tz_identifier: FunctionArg, /) -> FunctionCall:
    """
    Sets a specific timezone for a datetime. **Must be used in conjunction with DATETIME_FORMAT.** A list of supported timezone identifiers can be found `here <https://support.airtable.com/hc/en-us/articles/216141558-Supported-timezones-for-SET-TIMEZONE>`__.
    """
    return FunctionCall('SET_TIMEZONE', date, tz_identifier)


def SQRT(value: FunctionArg, /) -> FunctionCall:
    """
    Returns the square root of a nonnegative number.
    """
    return FunctionCall('SQRT', value)


def SUBSTITUTE(string: FunctionArg, old_text: FunctionArg, new_text: FunctionArg, index: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Replaces occurrences of old_text in string with new_text.
    """
    return FunctionCall('SUBSTITUTE', string, old_text, new_text, *(v for v in [index] if v is not None))


def SUM(number: FunctionArg, /, *numbers: FunctionArg) -> FunctionCall:
    """
    Sum together the numbers. Equivalent to number1 + number2 + ...
    """
    return FunctionCall('SUM', number, *numbers)


def SWITCH(expression: FunctionArg, pattern: FunctionArg, result: FunctionArg, /, *pattern_results: FunctionArg) -> FunctionCall:
    """
    Takes an expression, a list of possible values for that expression, and for each one, a value that the expression should take in that case. It can also take a default value if the expression input doesn't match any of the defined patterns. In many cases, SWITCH() can be used instead `of a nested IF() formula <https://support.airtable.com/hc/en-us/articles/360041812413>`__.
    """
    return FunctionCall('SWITCH', expression, pattern, result, *pattern_results)


def T(value: FunctionArg, /) -> FunctionCall:
    """
    Returns the argument if it is text and blank otherwise.
    """
    return FunctionCall('T', value)


def TIMESTR(timestamp: FunctionArg, /) -> FunctionCall:
    """
    Formats a datetime into a time-only string (HH:mm:ss).
    """
    return FunctionCall('TIMESTR', timestamp)


def TODAY() -> FunctionCall:
    """
    While similar to the NOW() function: TODAY() returns the current date (not the current time, if formatted, time will return 12:00am).
    """
    return FunctionCall('TODAY')


def TONOW(date: FunctionArg, /) -> FunctionCall:
    """
    Calculates the number of days between the current date and another date.
    """
    return FunctionCall('TONOW', date)


def TRIM(string: FunctionArg, /) -> FunctionCall:
    """
    Removes whitespace at the beginning and end of string.
    """
    return FunctionCall('TRIM', string)


def TRUE() -> FunctionCall:
    """
    Logical value true. The value of true is represented numerically by a 1.
    """
    return FunctionCall('TRUE')


def UPPER(string: FunctionArg, /) -> FunctionCall:
    """
    Makes string uppercase.
    """
    return FunctionCall('UPPER', string)


def VALUE(text: FunctionArg, /) -> FunctionCall:
    """
    Converts the text string to a number. Some exceptions apply—if the string contains certain mathematical operators(-,%) the result may not return as expected. In these scenarios we recommend using a combination of VALUE and REGEX_REPLACE to remove non-digit values from the string:
    """
    return FunctionCall('VALUE', text)


def WEEKDAY(date: FunctionArg, start_day_of_week: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Returns the day of the week as an integer between 0 (Sunday) and 6 (Saturday). You may optionally provide a second argument (either ``"Sunday"`` or ``"Monday"``) to start weeks on that day. If omitted, weeks start on Sunday by default.
    """
    return FunctionCall('WEEKDAY', date, *(v for v in [start_day_of_week] if v is not None))


def WEEKNUM(date: FunctionArg, start_day_of_week: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Returns the week number in a year. You may optionally provide a second argument (either ``"Sunday"`` or ``"Monday"``) to start weeks on that day. If omitted, weeks start on Sunday by default.
    """
    return FunctionCall('WEEKNUM', date, *(v for v in [start_day_of_week] if v is not None))


def WORKDAY(start_date: FunctionArg, num_days: FunctionArg, holidays: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Returns a date that is numDays working days after startDate. Working days exclude weekends and an optional list of holidays, formatted as a comma-separated string of ISO-formatted dates.
    """
    return FunctionCall('WORKDAY', start_date, num_days, *(v for v in [holidays] if v is not None))


def WORKDAY_DIFF(start_date: FunctionArg, end_date: FunctionArg, holidays: Optional[FunctionArg] = None, /) -> FunctionCall:
    """
    Counts the number of working days between startDate and endDate. Working days exclude weekends and an optional list of holidays, formatted as a comma-separated string of ISO-formatted dates.
    """
    return FunctionCall('WORKDAY_DIFF', start_date, end_date, *(v for v in [holidays] if v is not None))


def XOR(expression: FunctionArg, /, *expressions: FunctionArg) -> FunctionCall:
    """
    Returns true if an **odd** number of arguments are true.
    """
    return FunctionCall('XOR', expression, *expressions)


def YEAR(date: FunctionArg, /) -> FunctionCall:
    """
    Returns the four-digit year of a datetime.
    """
    return FunctionCall('YEAR', date)


# [[[end]]] (checksum: e89fb729872c20bdff0bf57c061dae96)
# fmt: on
