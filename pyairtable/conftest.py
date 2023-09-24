"""
Configuration for pyairtable doctests
"""

# This file is part of the test suite, not the library,
# so we don't type-check it. Annotations are for IDEs.
# mypy: ignore-errors

import datetime
import re
from importlib import import_module
from typing import Any, Dict
from unittest import mock

import pytest

import pyairtable
import pyairtable.models.collaborator
import pyairtable.models.comment
from pyairtable.testing import FakeAirtable


@pytest.fixture()
def fake_airtable(requests_mock):
    with FakeAirtable() as fake:
        yield fake


@pytest.fixture(autouse=True)
def annotate_doctest_namespace(
    doctest_namespace: Dict[str, Any], fake_airtable: FakeAirtable
):
    """
    Ensures our doctests do not need to import common methods/classes
    or reference objects that our documentation assumes the user has
    already created.
    """
    doctest_namespace["api"] = api = pyairtable.Api("patFakeForDoctest")
    doctest_namespace["base"] = base = api.base("appFakeForDoctest")
    doctest_namespace["table"] = table = base.table("tblFakeForDoctest")
    doctest_namespace["fake_airtable"] = fake_airtable
    table.add_comment("recThatHasComment", "Hello, @[usrVMNxslc6jG0Xed]!")

    for objpath in (
        "pyairtable",
        "pyairtable.Api",
        "pyairtable.Base",
        "pyairtable.Table",
    ):
        modpath, _, name = objpath.rpartition(".")
        if modpath:
            obj = getattr(import_module(modpath), name)
        else:
            obj = import_module(name)
        doctest_namespace[name] = obj

    now = datetime.datetime.utcnow().isoformat()
    fake_airtable.add_records(
        base,
        table,
        [
            {
                "id": "rec00W8eG2x0ew1Af",
                "createdTime": now,
                "fields": {
                    "Attachments": [
                        {
                            "id": "attW8eG2x0ew1Af",
                            "url": "https://example.com/hello.jpg",
                            "filename": "hello.jpg",
                        }
                    ],
                    "Barcode": {"type": "upce", "text": "01234567"},
                    "Click Me": {"label": "Click Me", "url": "http://example.com"},
                    "Created By": {
                        "id": "usrAdw9EjV90xbW",
                        "email": "alice@example.com",
                        "name": "Alice Arnold",
                    },
                    "Collaborators": [
                        {
                            "id": "usrAdw9EjV90xbW",
                            "email": "alice@example.com",
                            "name": "Alice Arnold",
                        },
                        {
                            "id": "usrAdw9EjV90xbX",
                            "email": "bob@example.com",
                            "name": "Bob Barker",
                        },
                    ],
                },
            },
            {
                "id": "recwPQIfs4wKPyc9D",
                "createdTime": now,
                "fields": {"First Name": "John", "Age": 20},
            },
            {"id": "recMNxslc6jG0XedV", "createdTime": now, "fields": {}},
        ],
    )
    fake_airtable.add_records(
        base,
        table,
        [
            {"id": "recAdw9EjV90xbcdW", "createdTime": now, "fields": {}},
            {"id": "recAdw9EjV90xbcdX", "createdTime": now, "fields": {}},
            {
                "id": "rec00W8eG2x0ew1Ac",
                "createdTime": now,
                "fields": {
                    "Collaborator": {
                        "id": "usrAdw9EjV90xbW",
                        "email": "alice@example.com",
                        "name": "Alice Arnold",
                    }
                },
            },
        ],
        immutable=True,
    )
    doctest_namespace["upserts"] = [
        {"id": "recAdw9EjV90xbcdX", "fields": {"Name": "Record X"}},
        {"fields": {"Name": "Record Y"}},
    ]


@pytest.fixture(autouse=True)
def custom_doctest_output_checker():
    """
    Allows us to put extra leading/trailing whitespace around nested objects
    (for the sake of readability in the documentation) without disrupting
    how doctest will compare expected vs actual output during test runs.
    """
    import _pytest.doctest

    old_check_output = _pytest.doctest.CHECKER_CLASS.check_output

    def check_output(self, want: str, got: str, optionflags: Any) -> bool:
        if want == got:
            return True
        want = re.sub(r"([\[\{\(])\s+", r"\1", want)
        want = re.sub(r"\s+([\]\}\)])", r"\1", want)
        return old_check_output(self, want, got, optionflags)

    with mock.patch("_pytest.doctest.CHECKER_CLASS.check_output", check_output):
        yield
