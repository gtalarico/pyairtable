import json
from collections import OrderedDict
from pathlib import Path
from posixpath import join as urljoin
from typing import Callable
from urllib.parse import quote, urlencode

import pytest
from mock import Mock
from requests import HTTPError

from pyairtable.api import Api, Base, Table


@pytest.fixture
def url_builder():
    """Builds Airtable Api Url Manually for mock testing"""

    def _url_builder(base_id, table_name, params=None):
        urltable_name = quote(table_name, safe="")
        url = urljoin(Api.endpoint_url, base_id, urltable_name)
        if params:
            params = OrderedDict(sorted(params.items()))
            url += "?" + urlencode(params)
        return url

    return _url_builder


@pytest.fixture
def constants():
    return dict(
        API_KEY="FakeApiKey", BASE_ID="appJMY16gZDQrMWpA", TABLE_NAME="Table Name"
    )


@pytest.fixture()
def api(constants) -> Api:
    return Api(constants["API_KEY"])


@pytest.fixture()
def base(api: Api, constants) -> Base:
    return api.base(constants["BASE_ID"])


@pytest.fixture()
def table(base: Base, constants) -> Table:
    return base.table(constants["TABLE_NAME"])


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
    """Each call will return the next response in mock_response_list"""
    i = iter(mock_response_list)

    def _response_iterator(request, context):
        return next(i)

    return _response_iterator


def http_error():
    raise HTTPError("Not Found")


@pytest.fixture
def response():
    response = Mock()
    response.raise_for_status.side_effect = http_error
    response.url = "page%20url"
    return response


@pytest.fixture
def sample_data():
    return Path(__file__).parent / "sample_data"


@pytest.fixture
def sample_json(sample_data: Path) -> Callable:
    def _get_sample_json(name):
        location = sample_data / f"{name}.json"
        with location.open() as fp:
            return json.load(fp)

    return _get_sample_json
