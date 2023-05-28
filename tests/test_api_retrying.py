"""
For these tests Mocker cannot be used because Retry is operating on a lower level.
Instead we use a real HTTP server running in a separate thread, which we can program
to respond with various HTTP status codes.
"""
import json
import os
import threading
from http import HTTPStatus
from urllib.parse import urljoin
from wsgiref.simple_server import make_server

import pytest
import requests

from pyairtable.api.retrying import retry_strategy
from pyairtable.api.table import Table


# Adapted from https://github.com/kevin1024/pytest-httpbin
class Server:
    """
    HTTP server running a WSGI application in its own thread.
    """

    port_envvar = "HTTPBIN_HTTP_PORT"

    def __init__(self, host="127.0.0.1", port=0, application=None, **kwargs):
        self.app = application
        if self.port_envvar in os.environ:
            port = int(os.environ[self.port_envvar])
        self._server = make_server(host, port, self.app, **kwargs)
        self.host = self._server.server_address[0]
        self.port = self._server.server_address[1]
        self.protocol = "http"

        self._thread = threading.Thread(
            name=self.__class__,
            target=self._server.serve_forever,
        )

    def __del__(self):
        if hasattr(self, "_server"):
            self.stop()

    def start(self):
        self._thread.start()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()
        suppress_exc = self._server.__exit__(*args, **kwargs)
        self._thread.join()
        return suppress_exc

    def __add__(self, other):
        return self.url + other

    def stop(self):
        self._server.shutdown()

    @property
    def url(self):
        return f"{self.protocol}://{self.host}:{self.port}"

    def join(self, url, allow_fragments=True):
        return urljoin(self.url, url, allow_fragments=allow_fragments)


class MockApi:
    """
    Dumb WSGI app that returns responses from a stack.
    """

    def __init__(self, responses=None):
        self.responses = responses or []

    def __call__(self, environ, start_response):
        if not self.responses:
            raise RuntimeError("MockApi.responses is empty")
        status, jsondata = self.responses.pop(0)
        if isinstance(status, int):
            status = f"{status} {HTTPStatus(status).phrase}"
        start_response(status, [("Content-Type", "application/json")])
        if jsondata is None:
            return []
        return [json.dumps(jsondata).encode("utf8")]


@pytest.fixture(scope="session")
def mock_endpoint():
    with Server(application=MockApi()) as server:
        yield server


@pytest.fixture
def table_with_retry_strategy(constants, mock_endpoint):
    def _table_with_retry(retry_strategy):
        return Table(
            constants["API_KEY"],
            constants["BASE_ID"],
            constants["TABLE_NAME"],
            timeout=(0.1, 0.1),
            retry_strategy=retry_strategy,
            endpoint_url=mock_endpoint.url,
        )

    return _table_with_retry


def test_retry_exceed(table_with_retry_strategy, mock_endpoint):
    strategy = retry_strategy(total=2, status_forcelist=[429])
    table = table_with_retry_strategy(strategy)

    mock_endpoint.app.responses = [(429, None)] * 3

    with pytest.raises(requests.exceptions.RetryError):
        table.get("record")


def test_retry_status_not_allowed(
    table_with_retry_strategy,
    mock_endpoint,
    mock_response_single,
):
    strategy = retry_strategy(total=2, status_forcelist=[429, 500])
    table = table_with_retry_strategy(strategy)

    mock_endpoint.app.responses = [
        (401, None),
        (200, mock_response_single),
    ]

    with pytest.raises(requests.exceptions.HTTPError):
        table.get("record")


def test_retry_eventual_success(
    table_with_retry_strategy,
    mock_endpoint,
    mock_response_single,
):
    strategy = retry_strategy(total=2, status_forcelist=[429, 500])
    table = table_with_retry_strategy(strategy)

    mock_endpoint.app.responses = [
        (429, None),
        (500, None),
        (200, mock_response_single),
    ]

    assert table.get("record") == mock_response_single
