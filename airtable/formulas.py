"""
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
        field_value = "'{}'".format(field_value)

    formula = "{{{name}}}={value}".format(name=field_name, value=field_value)
    return formula


# TODO
# def and_query(**params: dict) -> str:
#     params_str = ", ".join([f"{k}={repr(v)}" for k, v in params.items()])
#     return f"AND({params_str})"

# formula = and_query(**{"Name": "A", "Age": 20})
