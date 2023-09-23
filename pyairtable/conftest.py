"""
Configuration for pyairtable doctests
"""

# mypy: ignore-errors

import datetime
import pprint
import re
from importlib import import_module
from typing import Any
from unittest import mock

import pytest

import pyairtable
from pyairtable.testing import fake_airtable, fake_id


@pytest.fixture(autouse=True)
def annotate_doctest_namespace(doctest_namespace, monkeypatch, requests_mock):
    """
    Ensures our doctests do not need to import common methods/classes
    or reference objects that our documentation assumes the user has
    already created.
    """
    doctest_namespace["api"] = api = pyairtable.Api("FAKE API KEY")
    doctest_namespace["base"] = api.base(base := fake_id("app"))
    doctest_namespace["table"] = api.table(base, table := fake_id("tbl"))
    doctest_namespace["pprint"] = pprint.pprint

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

    with fake_airtable() as fake:
        doctest_namespace["fake_airtable"] = fake
        now = datetime.datetime.utcnow().isoformat()
        fake.add_records(
            base,
            table,
            [
                {
                    "id": "recW8eG2x0ew1Af",
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
                }
            ],
        )
        yield


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
