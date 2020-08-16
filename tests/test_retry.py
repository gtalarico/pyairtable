import pytest
from unittest import mock

from airtable import RateLimitRetry
from requests.exceptions import HTTPError


@pytest.fixture
def rate_error():
    exc = HTTPError()
    exc.response = mock.MagicMock()
    exc.response.status_code = 429
    return exc


@mock.patch("airtable.airtable.Airtable._request")
@mock.patch("airtable.airtable.time.sleep")
def test_retry(m_sleep, m_request, table, rate_error):
    # Raise Rate Error when airtable._request is called
    m_request.side_effect = rate_error

    with RateLimitRetry(table, wait_seconds=31):
        table.insert({})

    assert m_request.call_count == 3
    assert m_sleep.call_count == 3
    m_sleep.assert_called_with(31)


@mock.patch("airtable.airtable.Airtable._request")
@mock.patch("airtable.airtable.time.sleep")
def test_without_retry(m_sleep, m_request, table, rate_error):
    m_request.side_effect = rate_error
    table.insert({})

    assert m_request.call_count == 1
    assert not m_sleep.called
