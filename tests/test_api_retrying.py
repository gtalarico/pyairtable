"""
For these tests Mocker cannot be used because Retry is operating on a lower level.
Instead we use a real HTTP server running in a separate thread, which we can program
to respond with various HTTP status codes.
"""
import json
import threading
import time
from collections import deque
from http import HTTPStatus
from urllib.parse import urljoin
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest
import requests

from pyairtable.api import Api
from pyairtable.api.retrying import retry_strategy
from pyairtable.testing import fake_record


# Adapted from https://github.com/kevin1024/pytest-httpbin
class Server:
    """
    HTTP server running a WSGI application in its own thread.
    """

    def __init__(self, host="127.0.0.1", port=0, application=None, **kwargs):
        self.app = application
        self._server = make_server(host, port, self.app, **kwargs)
        self.host = self._server.server_address[0]
        self.port = self._server.server_address[1]
        self.protocol = "http"

        self._thread = threading.Thread(
            name=self.__class__,
            target=self._server.serve_forever,
        )

    def set_app(self, app):
        self.app = app
        self._server.set_app(app)

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


class QuietWSGIRequestHandler(WSGIRequestHandler):
    """
    Silences all log messages from the WSGI server.
    """

    def log_message(self, *args, **kwargs):
        return


class MockApi:
    """
    WSGI app that returns responses from a stack.
    """

    QPS = 5

    def __init__(self, responses=None, enforce_limit=True):
        """
        :param responses: If provided, should be a list of responses
            for the server to respond with, in first in first out order.
            Format should be ``list[tuple[status, serializable]]``,
            where ``status`` is either an ``int`` or ``str``,
            and ``serializable`` can be encoded by ``json.dumps``.

        :param enforce_limit: If ``True``, the MockApi will return
            a 429 whenever if there has been more than five requests
            within the past second. This is an attempt to simulate
            `Airtable's API limits <https://airtable.com/developers/web/api/rate-limits>`_.
        """
        self.canned_responses = responses or []
        self.enforce_limit = enforce_limit
        self.timestamps = deque(maxlen=self.QPS)  # limit is 5 requests/sec

    def __call__(self, environ, start_response):
        status, response = self.next_response()
        start_response(status, [("Content-Type", "application/json")])
        return [response]

    def next_response(self):
        if (
            self.enforce_limit
            and len(self.timestamps) == self.QPS
            and (time.time() - self.timestamps[0] < 1)
        ):
            return ("429 Too Many Requests", b"")
        if not self.canned_responses:
            raise RuntimeError("MockApi.responses is empty")
        self.timestamps.append(time.time())
        status, jsondata = self.canned_responses.pop(0)
        if isinstance(status, int):
            status = f"{status} {HTTPStatus(status).phrase}"
        response = b"" if jsondata is None else json.dumps(jsondata).encode("utf8")
        return (status, response)


@pytest.fixture(scope="session")
def mock_endpoint_server():
    """
    Fixture that starts a simple WSGI server running in a separate thread.
    Only created once per session; expects us to call `set_app()` on each test.
    """
    with Server(handler_class=QuietWSGIRequestHandler) as server:
        yield server


@pytest.fixture(autouse=True)
def mock_endpoint(mock_endpoint_server):
    """
    Fixture that creates a MockApi and attaches it to the running server.
    Sets ``autouse=True`` to ensure no cross-test pollution.
    """
    app = MockApi()
    mock_endpoint_server.set_app(app)
    return app


@pytest.fixture
def table_with_retry_strategy(constants, mock_endpoint_server):
    def _table_with_retry(retry_strategy):
        api = Api(
            api_key=constants["API_KEY"],
            timeout=(0.1, 0.1),
            retry_strategy=retry_strategy,
            endpoint_url=mock_endpoint_server.url,
        )
        return api.table(constants["BASE_ID"], constants["TABLE_NAME"])

    return _table_with_retry


def test_retry_exceed(table_with_retry_strategy, mock_endpoint):
    """
    Test that we raise a RetryError if we get too many retryable error codes.
    """
    strategy = retry_strategy(total=2, status_forcelist=[429])
    table = table_with_retry_strategy(strategy)

    mock_endpoint.canned_responses = [(429, None)] * 3

    with pytest.raises(requests.exceptions.RetryError):
        table.get("record")


def test_retry_status_not_allowed(
    table_with_retry_strategy,
    mock_endpoint,
    mock_response_single,
):
    """
    Test that our retry logic does not affect other HTTP error codes.
    """
    strategy = retry_strategy(total=2, status_forcelist=[429, 500])
    table = table_with_retry_strategy(strategy)

    mock_endpoint.canned_responses = [
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
    """
    Test that our retry logic succeeds if we eventually get a valid result.
    """
    strategy = retry_strategy(total=2, status_forcelist=[429, 500])
    table = table_with_retry_strategy(strategy)

    mock_endpoint.canned_responses = [
        (429, None),
        (500, None),
        (200, mock_response_single),
    ]

    assert table.get("record") == mock_response_single


def test_retry_during_iterate(table_with_retry_strategy, mock_endpoint):
    """
    Test that our default retry logic will be enough to get through several pages of data.
    Relies on ``mock_endpoint`` to return 429s whenever QPS goes over the limit.
    """
    table = table_with_retry_strategy(retry_strategy())

    page_count = 10
    per_page = 5  # real world number is 100, but we don't need that much data here
    page = {"records": [fake_record()] * per_page}
    mock_endpoint.canned_responses = [(200, {**page, "offset": "offset"})] * page_count
    mock_endpoint.canned_responses[-1] = (200, page)  # no offset on the last page

    records = table.all()
    assert len(records) == page_count * per_page
