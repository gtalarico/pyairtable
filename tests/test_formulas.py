from datetime import date, datetime, timezone
from decimal import Decimal
from fractions import Fraction

import pytest
from mock import call

import pyairtable.exceptions
from pyairtable import formulas as F
from pyairtable import orm
from pyairtable.formulas import AND, EQ, GT, GTE, LT, LTE, NE, NOT, OR
from pyairtable.testing import fake_meta


def test_equivalence():
    assert F.Formula("a") == F.Formula("a")
    assert F.Formula("a") != F.Formula("b")
    assert F.Formula("a") != "b"


def test_operators():
    lft = F.Formula("a")
    rgt = F.Formula("b")
    assert str(lft) == "a"
    assert str(lft & rgt) == "AND(a, b)"
    assert str(lft | rgt) == "OR(a, b)"
    assert str(~(lft & rgt)) == "NOT(AND(a, b))"
    assert repr(lft & rgt) == "AND(Formula('a'), Formula('b'))"
    assert repr(lft | rgt) == "OR(Formula('a'), Formula('b'))"
    assert repr(~F.Formula("a")) == "NOT(Formula('a'))"
    assert lft.flatten() is lft
    assert repr(lft ^ rgt) == "XOR(Formula('a'), Formula('b'))"
    assert str(lft ^ rgt) == "XOR(a, b)"


@pytest.mark.parametrize(
    "cmp,op",
    [
        (EQ, "="),
        (NE, "!="),
        (GT, ">"),
        (GTE, ">="),
        (LT, "<"),
        (LTE, "<="),
    ],
)
def test_comparisons(cmp, op):
    assert repr(cmp(1, 1)) == f"{cmp.__name__}(1, 1)"
    assert str(cmp(1, 1)) == f"1{op}1"
    assert str(cmp(F.Formula("Foo"), "Foo")) == f"Foo{op}'Foo'"


@pytest.mark.parametrize(
    "target",
    [
        F.Formula("X"),  # Formula
        F.Field("X"),  # Field
        F.EQ(1, 1),  # Comparison
        F.TODAY(),  # FunctionCall
    ],
)
@pytest.mark.parametrize(
    "shortcut,cmp",
    [
        ("eq", EQ),
        ("ne", NE),
        ("gt", GT),
        ("gte", GTE),
        ("lt", LT),
        ("lte", LTE),
    ],
)
def test_comparison_shortcuts(target, shortcut, cmp):
    """
    Test that methods like .eq() are exposed on all subclasses of Formula.
    """
    formula = getattr(target, shortcut)("Y")  # Field("X").eq("Y")
    assert formula == cmp(target, "Y")  # EQ(Field("X"), "Y")


def test_comparison_equivalence():
    assert EQ(1, 1) == EQ(1, 1)
    assert EQ(1, 2) != EQ(2, 1)
    assert EQ(1, 1) != NE(1, 1)
    assert EQ(1, 1) != F.Formula("1=1")


def test_comparison_is_abstract():
    with pytest.raises(NotImplementedError):
        F.Comparison("lft", "rgt")


@pytest.mark.parametrize("op", ("AND", "OR"))
def test_compound(op):
    cmp = F.Compound(op, [EQ("foo", 1), EQ("bar", 2)])
    assert repr(cmp) == f"{op}(EQ('foo', 1), EQ('bar', 2))"


@pytest.mark.parametrize("op", ("AND", "OR"))
def test_compound_with_iterable(op):
    cmp = F.Compound(op, (EQ(f"f{n}", n) for n in range(3)))
    assert repr(cmp) == f"{op}(EQ('f0', 0), EQ('f1', 1), EQ('f2', 2))"


def test_compound_equivalence():
    assert F.Compound("AND", [1]) == F.Compound("AND", [1])
    assert F.Compound("AND", [1]) != F.Compound("AND", [2])
    assert F.Compound("AND", [1]) != F.Compound("OR", [1])
    assert F.Compound("AND", [1]) != [1]


@pytest.mark.parametrize("cmp", [AND, OR])
@pytest.mark.parametrize(
    "call_args",
    [
        # mix *components and and **fields
        call(EQ("foo", 1), bar=2),
        # multiple *components
        call(EQ("foo", 1), EQ(F.Field("bar"), 2)),
        # one item in *components that is also an iterable
        call([EQ("foo", 1), EQ(F.Field("bar"), 2)]),
        call((EQ("foo", 1), EQ(F.Field("bar"), 2))),
        lambda: call(iter([EQ("foo", 1), EQ(F.Field("bar"), 2)])),
        # test that we accept `str` and convert to formulas
        call(["'foo'=1", "{bar}=2"]),
    ],
)
def test_compound_constructors(cmp, call_args):
    if type(call_args) is not type(call):
        call_args = call_args()
    compound = cmp(*call_args.args, **call_args.kwargs)
    expected = cmp(EQ("foo", 1), EQ(F.Field("bar"), 2))
    # compare final output expression, since the actual values will not be equal
    assert str(compound) == str(expected)


@pytest.mark.parametrize("cmp", ["AND", "OR", "NOT"])
def test_compound_without_parameters(cmp):
    with pytest.raises(
        ValueError,
        match=r"Compound\(\) requires at least one component",
    ):
        F.Compound(cmp, [])


def test_compound_flatten():
    a = EQ("a", "a")
    b = EQ("b", "b")
    c = EQ("c", "c")
    d = EQ("d", "d")
    e = EQ("e", "e")
    c = (a & b) & (c & (d | e))
    assert repr(c) == repr(
        AND(
            AND(EQ("a", "a"), EQ("b", "b")),
            AND(EQ("c", "c"), OR(EQ("d", "d"), EQ("e", "e"))),
        )
    )
    assert repr(c.flatten()) == repr(
        AND(
            EQ("a", "a"),
            EQ("b", "b"),
            EQ("c", "c"),
            OR(EQ("d", "d"), EQ("e", "e")),
        )
    )
    assert repr((~c).flatten()) == repr(
        NOT(
            AND(
                EQ("a", "a"),
                EQ("b", "b"),
                EQ("c", "c"),
                OR(EQ("d", "d"), EQ("e", "e")),
            )
        )
    )
    assert str((~c).flatten()) == (
        "NOT(AND('a'='a', 'b'='b', 'c'='c', OR('d'='d', 'e'='e')))"
    )


def test_compound_flatten_circular_dependency():
    circular = NOT(F.Formula("x"))
    circular.components = [circular]
    with pytest.raises(pyairtable.exceptions.CircularFormulaError):
        circular.flatten()


@pytest.mark.parametrize(
    "compound,expected",
    [
        (EQ(1, 1).eq(True), "(1=1)=TRUE()"),
        (EQ(False, EQ(1, 2)), "FALSE()=(1=2)"),
    ],
)
def test_compound_with_compound(compound, expected):
    assert str(compound) == expected


def test_not():
    assert str(NOT(EQ("foo", 1))) == "NOT('foo'=1)"
    assert str(NOT(foo=1)) == "NOT({foo}=1)"

    with pytest.raises(TypeError):
        NOT(EQ("foo", 1), EQ("bar", 2))

    with pytest.raises(ValueError, match="requires exactly one condition; got 2"):
        NOT(EQ("foo", 1), bar=2)

    with pytest.raises(ValueError, match="requires exactly one condition; got 2"):
        NOT(foo=1, bar=2)

    with pytest.raises(ValueError, match="requires exactly one condition; got 0"):
        NOT()


@pytest.mark.parametrize(
    "input,expected",
    [
        (EQ(F.Formula("a"), "b"), EQ(F.Formula("a"), "b")),
        (True, F.TRUE()),
        (False, F.FALSE()),
        (3, F.Formula("3")),
        (3.5, F.Formula("3.5")),
        (Decimal("3.14159265"), F.Formula("3.14159265")),
        (Fraction("4/19"), F.Formula("4/19")),
        ("asdf", F.Formula("'asdf'")),
        ("Jane's", F.Formula("'Jane\\'s'")),
        ([1, 2, 3], TypeError),
        ((1, 2, 3), TypeError),
        ({1, 2, 3}, TypeError),
        ({1: 2, 3: 4}, TypeError),
        (
            date(2023, 12, 1),
            F.DATETIME_PARSE("2023-12-01"),
        ),
        (
            datetime(2023, 12, 1, 12, 34, 56),
            F.DATETIME_PARSE("2023-12-01T12:34:56.000"),
        ),
        (
            datetime(2023, 12, 1, 12, 34, 56, tzinfo=timezone.utc),
            F.DATETIME_PARSE("2023-12-01T12:34:56.000Z"),
        ),
        (orm.fields.Field("Foo"), F.Field("Foo")),
    ],
)
def test_to_formula(input, expected):
    """
    Test that certain values are not changed at all by to_formula()
    """
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            F.to_formula(input)
    else:
        assert F.to_formula(input) == expected


@pytest.mark.parametrize(
    "input,expected",
    [
        (EQ(F.Formula("a"), "b"), "a='b'"),
        (True, "TRUE()"),
        (False, "FALSE()"),
        (3, "3"),
        (3.5, "3.5"),
        (Decimal("3.14159265"), "3.14159265"),
        (Fraction("4/19"), "4/19"),
        ("asdf", "'asdf'"),
        ("Jane's", "'Jane\\'s'"),
        ([1, 2, 3], TypeError),
        ((1, 2, 3), TypeError),
        ({1, 2, 3}, TypeError),
        ({1: 2, 3: 4}, TypeError),
        (
            date(2023, 12, 1),
            "DATETIME_PARSE('2023-12-01')",
        ),
        (
            datetime(2023, 12, 1, 12, 34, 56),
            "DATETIME_PARSE('2023-12-01T12:34:56.000')",
        ),
        (
            datetime(2023, 12, 1, 12, 34, 56, tzinfo=timezone.utc),
            "DATETIME_PARSE('2023-12-01T12:34:56.000Z')",
        ),
        (orm.fields.Field("Foo"), "{Foo}"),
    ],
)
def test_to_formula_str(input, expected):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            F.to_formula_str(input)
    else:
        assert F.to_formula_str(input) == expected


@pytest.mark.parametrize(
    "sig,expected",
    [
        (call({"Field": "value"}), "{Field}='value'"),
        (call({"A": ("=", 123), "B": ("!=", 123)}), "AND({A}=123, {B}!=123)"),
        (call({"A": 123, "B": 123}, match_any=True), "OR({A}=123, {B}=123)"),
        (call({"Field": ("<", 123)}), "{Field}<123"),
        (call({"Field": ("<=", 123)}), "{Field}<=123"),
        (call({"Field": (">", 123)}), "{Field}>123"),
        (call({"Field": (">=", 123)}), "{Field}>=123"),
    ],
)
def test_match(sig, expected):
    assert str(F.match(*sig.args, **sig.kwargs)) == expected


def test_match__exception():
    with pytest.raises(ValueError):
        F.match({})


def test_function_call():
    fc = F.FunctionCall("IF", 1, True, False)
    assert repr(fc) == "IF(1, True, False)"
    assert str(fc) == "IF(1, TRUE(), FALSE())"


def test_function_call_equivalence():
    assert F.TODAY() == F.TODAY()
    assert F.TODAY() != F.NOW()
    assert F.CEILING(1) == F.CEILING(1)
    assert F.CEILING(1) != F.CEILING(2)
    assert F.TODAY() != F.Formula("TODAY()")


@pytest.mark.parametrize(
    "input,expected",
    [
        ("First Name", "{First Name}"),
        ("Guest's Name", r"{Guest's Name}"),
        ("With {Curly Braces}", r"{With {Curly Braces\}}"),
    ],
)
def test_field_name(input, expected):
    assert F.field_name(input) == expected


def test_quoted():
    assert F.quoted("Guest") == "'Guest'"
    assert F.quoted("Guest's Name") == r"'Guest\'s Name'"
    assert F.quoted(F.quoted("Guest's Name")) == r"'\'Guest\\\'s Name\''"


class FakeModel(orm.Model):
    Meta = fake_meta()
    name = orm.fields.TextField("Name")
    email = orm.fields.EmailField("Email")
    phone = orm.fields.PhoneNumberField("Phone")


@pytest.mark.parametrize(
    "methodname,op",
    [
        ("eq", "="),
        ("ne", "!="),
        ("gt", ">"),
        ("gte", ">="),
        ("lt", "<"),
        ("lte", "<="),
    ],
)
def test_orm_field_comparison_shortcuts(methodname, op):
    """
    Test each shortcut method on an ORM field.
    """
    formula = getattr(FakeModel.name, methodname)("Value")
    assert F.to_formula_str(formula) == f"{{Name}}{op}'Value'"


def test_orm_field_as_formula():
    """
    Test different ways of using an ORM field in a formula.
    """
    formula = FakeModel.email.ne(F.BLANK()) | NE(FakeModel.phone, F.BLANK())
    formula &= FakeModel.name
    result = F.to_formula_str(formula.flatten())
    assert result == "AND(OR({Email}!=BLANK(), {Phone}!=BLANK()), {Name})"


@pytest.mark.parametrize(
    "fn,argcount",
    [
        ("ABS", 1),
        ("AVERAGE", 2),
        ("BLANK", 0),
        ("CEILING", 2),
        ("CONCATENATE", 2),
        ("COUNT", 2),
        ("COUNTA", 2),
        ("COUNTALL", 2),
        ("CREATED_TIME", 0),
        ("DATEADD", 3),
        ("DATESTR", 1),
        ("DATETIME_DIFF", 3),
        ("DATETIME_FORMAT", 2),
        ("DATETIME_PARSE", 3),
        ("DAY", 1),
        ("ENCODE_URL_COMPONENT", 1),
        ("ERROR", 0),
        ("EVEN", 1),
        ("EXP", 1),
        ("FALSE", 0),
        ("FIND", 3),
        ("FLOOR", 2),
        ("FROMNOW", 1),
        ("HOUR", 1),
        ("IF", 3),
        ("INT", 1),
        ("ISERROR", 1),
        ("IS_AFTER", 2),
        ("IS_BEFORE", 2),
        ("IS_SAME", 3),
        ("LAST_MODIFIED_TIME", 1),
        ("LEFT", 2),
        ("LEN", 1),
        ("LOG", 2),
        ("LOWER", 1),
        ("MAX", 2),
        ("MID", 3),
        ("MIN", 2),
        ("MINUTE", 1),
        ("MOD", 2),
        ("MONTH", 1),
        ("NOW", 0),
        ("ODD", 1),
        ("POWER", 2),
        ("RECORD_ID", 0),
        ("REGEX_EXTRACT", 2),
        ("REGEX_MATCH", 2),
        ("REGEX_REPLACE", 3),
        ("REPLACE", 4),
        ("REPT", 2),
        ("RIGHT", 2),
        ("ROUND", 2),
        ("ROUNDDOWN", 2),
        ("ROUNDUP", 2),
        ("SEARCH", 3),
        ("SECOND", 1),
        ("SET_LOCALE", 2),
        ("SET_TIMEZONE", 2),
        ("SQRT", 1),
        ("SUBSTITUTE", 4),
        ("SUM", 2),
        ("SWITCH", 4),
        ("T", 1),
        ("TIMESTR", 1),
        ("TODAY", 0),
        ("TONOW", 1),
        ("TRIM", 1),
        ("TRUE", 0),
        ("UPPER", 1),
        ("VALUE", 1),
        ("WEEKDAY", 2),
        ("WEEKNUM", 2),
        ("WORKDAY", 3),
        ("WORKDAY_DIFF", 3),
        ("XOR", 2),
        ("YEAR", 1),
    ],
)
def test_function_calls(fn, argcount):
    """
    Test that the function call shortcuts in the formulas module
    all behave as expected with the given number of arguments.
    """
    args = tuple(f"arg{n}" for n in range(1, argcount + 1))
    args_repr = ", ".join(repr(arg) for arg in args)
    args_formula = ", ".join(F.to_formula_str(arg) for arg in args)
    result = getattr(F, fn)(*args)
    assert isinstance(result, F.FunctionCall)
    assert result.name == fn
    assert result.args == args
    assert repr(result) == f"{fn}({args_repr})"
    assert str(result) == f"{fn}({args_formula})"
