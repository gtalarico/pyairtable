"""
Configuration for pyairtable doctests
"""

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
import pyairtable.testing
from pyairtable.testing import FakeAirtable, fake_id


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
    doctest_namespace["api"] = api = pyairtable.Api("patX9e810wHn3mMLz")
    doctest_namespace["base"] = api.base(base := fake_id("app"))
    doctest_namespace["table"] = api.table(base, table := fake_id("tbl"))

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

    doctest_namespace["fake_airtable"] = fake_airtable
    now = datetime.datetime.utcnow().isoformat()
    fake_airtable.add_records(
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
            },
            {
                "id": "recwPQIfs4wKPyc9D",
                "createdTime": now,
                "fields": {"First Name": "John", "Age": 20},
            },
        ],
    )
    fake_airtable.add_records(
        base,
        table,
        [
            {"id": "recAdw9EjV90xbW", "createdTime": now, "fields": {}},
            {"id": "recAdw9EjV90xbX", "createdTime": now, "fields": {}},
            {
                "id": "recW8eG2x0ew1Ac",
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
    fake_airtable._comments["recMNxslc6jG0XedV"] = [
        pyairtable.models.comment.Comment(
            id="comdVMNxslc6jG0Xe",
            text="Hello, @[usrVMNxslc6jG0Xed]!",
            created_time="2023-06-07T17:46:24.435891",
            last_updated_time=None,
            mentioned={
                "usrVMNxslc6jG0Xed": pyairtable.models.comment.Comment.Mentioned(
                    display_name="Alice",
                    email="alice@example.com",
                    id="usrVMNxslc6jG0Xed",
                    type="user",
                )
            },
            author=pyairtable.models.collaborator.Collaborator(
                id="usr0000pyairtable",
                email="pyairtable@example.com",
                name="Your pyairtable access token",
            ),
        )
    ]
    doctest_namespace["upserts"] = [
        {"id": "recAdw9EjV90xbX", "fields": {"Name": "Record X"}},
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
