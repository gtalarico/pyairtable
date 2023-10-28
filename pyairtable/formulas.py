"""
This module exports building blocks for constructing Airtable formulas,
including function call proxies for all formula functions as of Dec '23.

See :doc:`formulas` for more information.
"""

import datetime
import re
from decimal import Decimal
from fractions import Fraction
from typing import Any, ClassVar, Iterable, List, Optional, Set, Union

from typing_extensions import Self as SelfType

from pyairtable.api.types import Fields
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

    def __and__(self, other: "Formula") -> "Formula":
        return AND(self, other)

    def __or__(self, other: "Formula") -> "Formula":
        return OR(self, other)

    def __xor__(self, other: "Formula") -> "Formula":
        return XOR(self, other)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Formula):
            return False
        return other.value == self.value

    def __invert__(self) -> "Formula":
        return NOT(self)

    def flatten(self) -> "Formula":
        return self

    def eq(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.EQ` comparison using this field.
        """
        return EQ(self, value)

    def ne(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.NE` comparison using this field.
        """
        return NE(self, value)

    def gt(self, value: Any) -> "Comparison":
        """
        Build a :class:`~pyairtable.formulas.GT` comparison using this field.
        """
        return GT(self, value)

    def lt(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.LT` comparison using this field.
        """
        return LT(self, value)

    def gte(self, value: Any) -> "Comparison":
        """
        Build a :class:`~pyairtable.formulas.GTE` comparison using this field.
        """
        return GTE(self, value)

    def lte(self, value: Any) -> "Comparison":
        """
        Build an :class:`~pyairtable.formulas.LTE` comparison using this field.
        """
        return LTE(self, value)


class Field(Formula):
    """
    Represents a field name.
    """

    def __str__(self) -> str:
        return "{%s}" % escape_quotes(self.value)


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
                raise CircularDependency(item)
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


class CircularDependency(RecursionError):
    """
    A circular dependency was encountered when flattening nested conditions.
    """


def match(field_values: Fields, *, match_any: bool = False) -> Optional[Formula]:
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
        return None
    if len(expressions) == 1:
        return expressions[0]
    if match_any:
        return OR(*expressions)
    return AND(*expressions)


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
    # Runtime import to avoid circular dependency
    from pyairtable import orm

    if isinstance(value, Formula):
        return str(value)
    if isinstance(value, bool):
        return "TRUE()" if value else "FALSE()"
    if isinstance(value, (int, float, Decimal, Fraction)):
        return str(value)
    if isinstance(value, str):
        return "'{}'".format(escape_quotes(value))
    if isinstance(value, datetime.datetime):
        return str(DATETIME_PARSE(datetime_to_iso_str(value)))
    if isinstance(value, datetime.date):
        return str(DATETIME_PARSE(date_to_iso_str(value)))
    if isinstance(value, orm.fields.Field):
        return field_name(value.field_name)
    raise TypeError(value, type(value))


def quoted(value: str) -> str:
    r"""
    Wrap string in quotes. This is needed when referencing a string inside a formula.
    Quotes are escaped.

    >>> quoted("John")
    "'John'"
    >>> quoted("Guest's Name")
    "'Guest\\'s Name'"
    """
    return "'{}'".format(escape_quotes(str(value)))


def escape_quotes(value: str) -> str:
    r"""
    Ensure any quotes are escaped. Already escaped quotes are ignored.

    Args:
        value: text to be escaped

    Usage:
        >>> escape_quotes(r"Player's Name")
        "Player\\'s Name"
        >>> escape_quotes(r"Player\'s Name")
        "Player\\'s Name"
    """
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
        "{Guest\\'s Name}"
    """
    return "{%s}" % escape_quotes(name)


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

    def __init__(self, name: str, *args: List[Any]):
        self.name = name
        self.args = args

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
    name, argspec = definition.rstrip(")").split("(")
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
    signature = [f"{arg}: Any" for arg in required]
    params = [*required]
    splat = optional.pop().rstrip(".") if optional and optional[-1].endswith("...") else None

    if optional:
        signature += [f"{arg}: Optional[Any] = None" for arg in optional]
        params += ["*(v for v in [" + ", ".join(optional) + "] if v is not None)"]

    if required or optional:
        signature += ["/"]

    if splat:
        signature += [f"*{splat}: Any"]
        params += [f"*{splat}"]

    joined_signature = ", ".join(signature)
    joined_params = (", " + ", ".join(params)) if params else ""

    cog.outl(f"def {name}({joined_signature}) -> FunctionCall:  # pragma: no cover")
    cog.outl(f"    \"\"\"")
    cog.outl(f"    Produce a formula that calls ``{name}()``")
    cog.outl(f"    \"\"\"")
    cog.outl(f"    return FunctionCall({name!r}{joined_params})")
    cog.outl("\n")

[[[out]]]"""


def ABS(value: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ABS()``
    """
    return FunctionCall('ABS', value)


def AVERAGE(number1: Any, /, *numbers: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``AVERAGE()``
    """
    return FunctionCall('AVERAGE', number1, *numbers)


def BLANK() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``BLANK()``
    """
    return FunctionCall('BLANK')


def CEILING(value: Any, significance: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``CEILING()``
    """
    return FunctionCall('CEILING', value, *(v for v in [significance] if v is not None))


def CONCATENATE(text1: Any, /, *texts: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``CONCATENATE()``
    """
    return FunctionCall('CONCATENATE', text1, *texts)


def COUNT(number1: Any, /, *numbers: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``COUNT()``
    """
    return FunctionCall('COUNT', number1, *numbers)


def COUNTA(text_or_number1: Any, /, *numbers: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``COUNTA()``
    """
    return FunctionCall('COUNTA', text_or_number1, *numbers)


def COUNTALL(text_or_number1: Any, /, *numbers: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``COUNTALL()``
    """
    return FunctionCall('COUNTALL', text_or_number1, *numbers)


def CREATED_TIME() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``CREATED_TIME()``
    """
    return FunctionCall('CREATED_TIME')


def DATEADD(date: Any, number: Any, units: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``DATEADD()``
    """
    return FunctionCall('DATEADD', date, number, units)


def DATESTR(date: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``DATESTR()``
    """
    return FunctionCall('DATESTR', date)


def DATETIME_DIFF(date1: Any, date2: Any, units: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``DATETIME_DIFF()``
    """
    return FunctionCall('DATETIME_DIFF', date1, date2, units)


def DATETIME_FORMAT(date: Any, output_format: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``DATETIME_FORMAT()``
    """
    return FunctionCall('DATETIME_FORMAT', date, *(v for v in [output_format] if v is not None))


def DATETIME_PARSE(date: Any, input_format: Optional[Any] = None, locale: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``DATETIME_PARSE()``
    """
    return FunctionCall('DATETIME_PARSE', date, *(v for v in [input_format, locale] if v is not None))


def DAY(date: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``DAY()``
    """
    return FunctionCall('DAY', date)


def ENCODE_URL_COMPONENT(component_string: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ENCODE_URL_COMPONENT()``
    """
    return FunctionCall('ENCODE_URL_COMPONENT', component_string)


def ERROR() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ERROR()``
    """
    return FunctionCall('ERROR')


def EVEN(value: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``EVEN()``
    """
    return FunctionCall('EVEN', value)


def EXP(power: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``EXP()``
    """
    return FunctionCall('EXP', power)


def FALSE() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``FALSE()``
    """
    return FunctionCall('FALSE')


def FIND(string_to_find: Any, where_to_search: Any, start_from_position: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``FIND()``
    """
    return FunctionCall('FIND', string_to_find, where_to_search, *(v for v in [start_from_position] if v is not None))


def FLOOR(value: Any, significance: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``FLOOR()``
    """
    return FunctionCall('FLOOR', value, *(v for v in [significance] if v is not None))


def FROMNOW(date: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``FROMNOW()``
    """
    return FunctionCall('FROMNOW', date)


def HOUR(datetime: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``HOUR()``
    """
    return FunctionCall('HOUR', datetime)


def IF(expression: Any, value1: Any, value2: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``IF()``
    """
    return FunctionCall('IF', expression, value1, value2)


def INT(value: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``INT()``
    """
    return FunctionCall('INT', value)


def ISERROR(expr: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ISERROR()``
    """
    return FunctionCall('ISERROR', expr)


def IS_AFTER(date1: Any, date2: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``IS_AFTER()``
    """
    return FunctionCall('IS_AFTER', date1, date2)


def IS_BEFORE(date1: Any, date2: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``IS_BEFORE()``
    """
    return FunctionCall('IS_BEFORE', date1, date2)


def IS_SAME(date1: Any, date2: Any, unit: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``IS_SAME()``
    """
    return FunctionCall('IS_SAME', date1, date2, unit)


def LAST_MODIFIED_TIME(*fields: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``LAST_MODIFIED_TIME()``
    """
    return FunctionCall('LAST_MODIFIED_TIME', *fields)


def LEFT(string: Any, how_many: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``LEFT()``
    """
    return FunctionCall('LEFT', string, how_many)


def LEN(string: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``LEN()``
    """
    return FunctionCall('LEN', string)


def LOG(number: Any, base: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``LOG()``
    """
    return FunctionCall('LOG', number, *(v for v in [base] if v is not None))


def LOWER(string: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``LOWER()``
    """
    return FunctionCall('LOWER', string)


def MAX(number1: Any, /, *numbers: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``MAX()``
    """
    return FunctionCall('MAX', number1, *numbers)


def MID(string: Any, where_to_start: Any, count: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``MID()``
    """
    return FunctionCall('MID', string, where_to_start, count)


def MIN(number1: Any, /, *numbers: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``MIN()``
    """
    return FunctionCall('MIN', number1, *numbers)


def MINUTE(datetime: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``MINUTE()``
    """
    return FunctionCall('MINUTE', datetime)


def MOD(value1: Any, divisor: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``MOD()``
    """
    return FunctionCall('MOD', value1, divisor)


def MONTH(date: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``MONTH()``
    """
    return FunctionCall('MONTH', date)


def NOW() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``NOW()``
    """
    return FunctionCall('NOW')


def ODD(value: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ODD()``
    """
    return FunctionCall('ODD', value)


def POWER(base: Any, power: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``POWER()``
    """
    return FunctionCall('POWER', base, power)


def RECORD_ID() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``RECORD_ID()``
    """
    return FunctionCall('RECORD_ID')


def REGEX_EXTRACT(string: Any, regex: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``REGEX_EXTRACT()``
    """
    return FunctionCall('REGEX_EXTRACT', string, regex)


def REGEX_MATCH(string: Any, regex: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``REGEX_MATCH()``
    """
    return FunctionCall('REGEX_MATCH', string, regex)


def REGEX_REPLACE(string: Any, regex: Any, replacement: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``REGEX_REPLACE()``
    """
    return FunctionCall('REGEX_REPLACE', string, regex, replacement)


def REPLACE(string: Any, start_character: Any, number_of_characters: Any, replacement: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``REPLACE()``
    """
    return FunctionCall('REPLACE', string, start_character, number_of_characters, replacement)


def REPT(string: Any, number: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``REPT()``
    """
    return FunctionCall('REPT', string, number)


def RIGHT(string: Any, how_many: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``RIGHT()``
    """
    return FunctionCall('RIGHT', string, how_many)


def ROUND(value: Any, precision: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ROUND()``
    """
    return FunctionCall('ROUND', value, precision)


def ROUNDDOWN(value: Any, precision: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ROUNDDOWN()``
    """
    return FunctionCall('ROUNDDOWN', value, precision)


def ROUNDUP(value: Any, precision: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``ROUNDUP()``
    """
    return FunctionCall('ROUNDUP', value, precision)


def SEARCH(string_to_find: Any, where_to_search: Any, start_from_position: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SEARCH()``
    """
    return FunctionCall('SEARCH', string_to_find, where_to_search, *(v for v in [start_from_position] if v is not None))


def SECOND(datetime: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SECOND()``
    """
    return FunctionCall('SECOND', datetime)


def SET_LOCALE(date: Any, locale_modifier: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SET_LOCALE()``
    """
    return FunctionCall('SET_LOCALE', date, locale_modifier)


def SET_TIMEZONE(date: Any, tz_identifier: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SET_TIMEZONE()``
    """
    return FunctionCall('SET_TIMEZONE', date, tz_identifier)


def SQRT(value: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SQRT()``
    """
    return FunctionCall('SQRT', value)


def SUBSTITUTE(string: Any, old_text: Any, new_text: Any, index: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SUBSTITUTE()``
    """
    return FunctionCall('SUBSTITUTE', string, old_text, new_text, *(v for v in [index] if v is not None))


def SUM(number1: Any, /, *numbers: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SUM()``
    """
    return FunctionCall('SUM', number1, *numbers)


def SWITCH(expression: Any, pattern: Any, result: Any, /, *pattern_results: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``SWITCH()``
    """
    return FunctionCall('SWITCH', expression, pattern, result, *pattern_results)


def T(value1: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``T()``
    """
    return FunctionCall('T', value1)


def TIMESTR(timestamp: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``TIMESTR()``
    """
    return FunctionCall('TIMESTR', timestamp)


def TODAY() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``TODAY()``
    """
    return FunctionCall('TODAY')


def TONOW(date: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``TONOW()``
    """
    return FunctionCall('TONOW', date)


def TRIM(string: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``TRIM()``
    """
    return FunctionCall('TRIM', string)


def TRUE() -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``TRUE()``
    """
    return FunctionCall('TRUE')


def UPPER(string: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``UPPER()``
    """
    return FunctionCall('UPPER', string)


def VALUE(text: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``VALUE()``
    """
    return FunctionCall('VALUE', text)


def WEEKDAY(date: Any, start_day_of_week: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``WEEKDAY()``
    """
    return FunctionCall('WEEKDAY', date, *(v for v in [start_day_of_week] if v is not None))


def WEEKNUM(date: Any, start_day_of_week: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``WEEKNUM()``
    """
    return FunctionCall('WEEKNUM', date, *(v for v in [start_day_of_week] if v is not None))


def WORKDAY_DIFF(start_date: Any, end_date: Any, holidays: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``WORKDAY_DIFF()``
    """
    return FunctionCall('WORKDAY_DIFF', start_date, end_date, *(v for v in [holidays] if v is not None))


def WORKDAY(start_date: Any, num_days: Any, holidays: Optional[Any] = None, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``WORKDAY()``
    """
    return FunctionCall('WORKDAY', start_date, num_days, *(v for v in [holidays] if v is not None))


def XOR(expression1: Any, /, *expressions: Any) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``XOR()``
    """
    return FunctionCall('XOR', expression1, *expressions)


def YEAR(date: Any, /) -> FunctionCall:  # pragma: no cover
    """
    Produce a formula that calls ``YEAR()``
    """
    return FunctionCall('YEAR', date)


# [[[end]]] (checksum: 428ee7de15bc4cd4dd46f2d4eb8b4043)
# fmt: on
