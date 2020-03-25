import random
import string
from datetime import datetime
import time
import pytest
from collections import OrderedDict
from posixpath import join as urljoin

from requests import HTTPError
from six.moves.urllib.parse import urlencode, quote
from mock import Mock

from airtable import Airtable


def rand_string_letter_digit(length):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


@pytest.fixture
def url_builder():
    """ Builds Airtable Api Url Manually for mock testing """

    def _url_builder(base_key, table_name, params=None):
        urltable_name = quote(table_name, safe="")
        url = urljoin(Airtable.API_URL, base_key, urltable_name)
        if params:
            params = OrderedDict(sorted(params.items()))
            url += "?" + urlencode(params)
        return url

    return _url_builder


@pytest.fixture
def constants():
    return dict(
        API_KEY="FakeApiKey", BASE_KEY="appJMY16gZDQrMWpA", TABLE_NAME="Table Name"
    )


@pytest.fixture()
def table(constants):
    return Airtable(
        constants["BASE_KEY"], constants["TABLE_NAME"], api_key=constants["API_KEY"]
    )


@pytest.fixture
def mock_records():
    return [
        {
            "id": "recH73JJvr7vv1234",
            "fields": {"SameField": 1234, "Value": "abc"},
            "createdTime": "2017-06-06T18:30:57.000Z",
        },
        {
            "id": "recyXhbY4uax4567",
            "fields": {"SameField": 456, "Value": "def"},
            "createdTime": "2017-06-06T18:30:57.000Z",
        },
        {
            "id": "recyXhbY4uax891",
            "fields": {"SameField": 789, "Value": "xyz"},
            "createdTime": "2017-06-06T18:30:57.000Z",
        },
    ]


@pytest.fixture
def create_random_record():
    return lambda: {
        "id": "rec" + rand_string_letter_digit(14),
        "fields": {
            "SameFields": random.randint(100, 9999),
            "Value": rand_string_letter_digit(5),
        },
        "createdTime": datetime.fromtimestamp(
            random.randint(1, int(time.time()))
        ).isoformat(),
    }


@pytest.fixture
def create_random_records(create_random_record):
    return lambda size: [create_random_record() for _ in range(size)]


@pytest.fixture
def mock_response_single(mock_records):
    return mock_records[0]


@pytest.fixture
def mock_response_list(mock_records):
    return [
        {"records": mock_records[0:2], "offset": "recuOeLpF6TQpArJi"},
        {"records": [mock_records[2]]},
    ]


@pytest.fixture
def mock_response_insert(mock_records):
    {
        "id": "rec9MgW8WhqcbnBx4",
        "fields": {
            "Editorial": ["recdaBsWECUC2aml3"],
            "Persona": "Startup CEO",
            "Verticals": ["recpI1hFWtSrbw5XI"],
            "Content Types": ["How-to posts", "Tutorials"],
            "Notes": "Driven by high impact; looking for ways to implement data driven initiatives",
        },
        "createdTime": "2017-06-06T18:31:12.000Z",
    }


@pytest.fixture
def mock_response_iterator(mock_response_list):
    """ Each call will return the next response in mock_response_list """
    i = iter(mock_response_list)

    def _response_iterator(request, context):
        v = next(i)
        return v

    return _response_iterator


def http_error():
    raise HTTPError("Not Found")


@pytest.fixture
def response():
    response = Mock()
    response.raise_for_status.side_effect = http_error
    response.url = "page%20url"
    return response
