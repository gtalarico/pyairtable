from airtable.formulas import AND, EQUAL, FIELD, STRING_VALUE, field_equals_value


def test_equal():
    assert EQUAL("A", "B") == "A=B"


def test_field():
    assert FIELD("Name") == "{Name}"


def test_and():
    assert AND("A", "B", "C") == "AND(A,B,C)"


def test_string_value():
    assert STRING_VALUE("A") == "'A'"


def test_combination():
    formula = AND(
        EQUAL(FIELD("First Name"), STRING_VALUE("A")),
        EQUAL(FIELD("Last Name"), STRING_VALUE("B")),
        EQUAL(FIELD("Age"), STRING_VALUE(15)),
    )
    assert formula == ("AND({First Name}='A',{Last Name}='B',{Age}='15')")


def test_field_equals_value():
    formula = field_equals_value("First Name", "John")
    assert formula == "{First Name}='John'"
