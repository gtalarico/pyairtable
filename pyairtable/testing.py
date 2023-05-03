"""
Helper functions for writing tests that use the pyairtable library.
"""
import datetime
import random
import string


def fake_id(type="rec", value=None):
    """
    Generates a fake Airtable-style ID.

    Keyword Args:
        type: the object type prefix, defaults to "rec"
        value: any value to use as the ID, defaults to random letters and digits

    >>> fake_id()
    'rec...'
    >>> fake_id('tbl')
    'tbl...'
    >>> fake_id(value='12345')
    'rec00000000012345'
    """
    if value is None:
        value = "".join(random.sample(string.ascii_letters + string.digits, 14))
    return type + f"{value:0>14}"[:14]


def fake_meta(
    base_id="appFakeTestingApp",
    table_name="tblFakeTestingTbl",
    api_key="patFakePersonalAccessToken",
):
    """
    Returns a ``Meta`` class for inclusion in a ``Model`` subclass.
    """
    attrs = {"base_id": base_id, "table_name": table_name, "api_key": api_key}
    return type("Meta", (), attrs)


def fake_record(fields=None, id=None, **other_fields):
    """
    Returns a fake record dict with the given field values.

    >>> fake_record({"Name": "Alice"})
    {'id': '...', 'createdTime': '...', 'fields': {'Name': 'Alice'}}

    >>> fake_record(name='Alice', address='123 Fake St')
    {'id': '...', 'createdTime': '...', 'fields': {'name': 'Alice', 'address': '123 Fake St'}}

    >>> fake_record(name='Alice', id='123')
    {'id': 'rec00000000000123', 'createdTime': '...', 'fields': {'name': 'Alice'}}
    """
    return {
        "id": fake_id(value=id),
        "createdTime": datetime.datetime.now().isoformat() + "Z",
        "fields": {**(fields or {}), **other_fields},
    }
