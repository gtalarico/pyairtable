"""
For these tests Mocker cannot be used because Retry is operating on a lower level
"""
import io
import json
from http.client import HTTPMessage, HTTPResponse
from unittest import mock

import pytest
import requests

from pyairtable.api.retrying import retry_strategy
from pyairtable.api.table import Table


@pytest.fixture
def table_with_retry_strategy(constants):
    def _table_with_retry(retry_strategy):
        return Table(
            constants["API_KEY"],
            constants["BASE_ID"],
            constants["TABLE_NAME"],
            timeout=(0.1, 0.1),
            retry_strategy=retry_strategy,
        )

    return _table_with_retry


@mock.patch("urllib3.connectionpool.HTTPConnectionPool._get_conn")
def test_retry_exceed(m, table_with_retry_strategy):
    strategy = retry_strategy(total=2, status_forcelist=[429])
    table = table_with_retry_strategy(strategy)

    m.return_value.getresponse.side_effect = [
        make_http_response_error(429),
        make_http_response_error(429),
        make_http_response_error(429),
    ]

    with pytest.raises(requests.exceptions.RetryError):
        table.get("record")

    assert len(m.return_value.request.mock_calls) == 3


@mock.patch("urllib3.connectionpool.HTTPConnectionPool._get_conn")
def test_retry_status_not_allowed(m, table_with_retry_strategy, mock_response_single):
    strategy = retry_strategy(total=2, status_forcelist=[429, 500])
    table = table_with_retry_strategy(strategy)

    response = make_response(mock_response_single, 200)

    m.return_value.getresponse.side_effect = [
        make_http_response_error(401),
        response,
    ]

    with pytest.raises(requests.exceptions.HTTPError):
        response = table.get("record")

    assert len(m.return_value.request.mock_calls) == 1


@mock.patch("urllib3.connectionpool.HTTPConnectionPool._get_conn")
def test_retry_eventual_success(m, table_with_retry_strategy, mock_response_single):
    strategy = retry_strategy(total=2, status_forcelist=[429, 500])
    table = table_with_retry_strategy(strategy)

    response = make_response(mock_response_single, 200)

    m.return_value.getresponse.side_effect = [
        make_http_response_error(429),
        make_http_response_error(500),
        response,
    ]

    response = table.get("record")
    assert response == mock_response_single
    assert len(m.return_value.request.mock_calls) == 3


# Test Helpers


def make_response(body: dict, status=200) -> HTTPResponse:
    headers = HTTPMessage()
    body_bytes = json.dumps(body).encode()

    sock = FakeSocketHelper(body_bytes)
    response = HTTPResponse(sock)  # type: ignore
    response.chunked = False  # type: ignore
    response.length = len(body_bytes)  # type: ignore
    response.status = status
    response.msg = headers
    return response


def make_http_response_error(status: int):
    return mock.Mock(status=status, msg=HTTPMessage())


class FakeSocketHelper:
    def __init__(self, text):
        if isinstance(text, str):
            text = text.encode("ascii")
        self.text = text
        self.data = b""
        self.file_closed = False

    def makefile(self, mode, bufsize=None):
        self.file = io.BytesIO(self.text)
        return self.file
