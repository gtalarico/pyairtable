import pytest
from pyairtable.formulas import (
    AND,
    OR,
    EQUAL,
    FIELD,
    STR_VALUE,
    IF,
    match,
    escape_quotes,
    FIND,
)


def test_equal():
    assert EQUAL("A", "B") == "A=B"


def test_field():
    assert FIELD("Name") == "{Name}"
    assert FIELD("Guest's Name") == r"{Guest\'s Name}"


def test_and():
    assert AND("A", "B", "C") == "AND(A,B,C)"


def test_or():
    assert OR("A", "B", "C") == "OR(A,B,C)"


def test_if():
    assert IF(1, 0, 1) == "IF(1, 0, 1)"


def test_find():
    rv = FIND(STR_VALUE(2021), FIELD("DatetimeCol"))
    assert rv == "FIND('2021', {DatetimeCol})"
    rv = FIND(STR_VALUE(2021), FIELD("DatetimeCol"), 2)
    assert rv == "FIND('2021', {DatetimeCol}, 2)"


def test_string_value():
    assert STR_VALUE("A") == "'A'"


def test_combination():
    formula = AND(
        EQUAL(FIELD("First Name"), STR_VALUE("A")),
        EQUAL(FIELD("Last Name"), STR_VALUE("B")),
        EQUAL(FIELD("Age"), STR_VALUE(15)),
    )
    assert formula == ("AND({First Name}='A',{Last Name}='B',{Age}='15')")


@pytest.mark.parametrize(
    "dict,exprected_formula",
    [
        ({"First Name": "John"}, "{First Name}='John'"),
        ({"A": "1", "B": "2"}, "AND({A}='1',{B}='2')"),
        ({}, ""),
    ],
)
def test_match(dict, exprected_formula):
    rv = match(dict)
    assert rv == exprected_formula


@pytest.mark.parametrize(
    "text,escaped",
    [
        ("hello", "hello"),
        ("player's name", r"player\'s name"),
        (r"player\'s name", r"player\'s name"),
    ],
)
def test_escape_quotes(text, escaped):
    rv = escape_quotes(text)
    assert rv == escaped
