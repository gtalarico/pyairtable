import datetime
import json
import math
from operator import attrgetter

import pytest

import pyairtable.models.webhook
from pyairtable.models.webhook import Webhook, WebhookNotification, WebhookPayload


@pytest.fixture
def webhook(sample_json, base, api):
    webhook_json = sample_json("Webhook")
    return Webhook.from_api(
        api=api,
        url=f"{base.webhooks_url}/{webhook_json['id']}",
        obj=webhook_json,
    )


@pytest.fixture
def payload_json(sample_json):
    return sample_json("WebhookPayload")


@pytest.mark.parametrize(
    "clsname",
    [
        "Webhook",
        "WebhookNotification",
        "WebhookPayload",
        "WebhookPayload.TableChanged",
    ],
)
def test_parse(sample_json, clsname):
    cls = attrgetter(clsname)(pyairtable.models.webhook)
    cls.parse_obj(sample_json(clsname))


@pytest.mark.parametrize(
    "method,expected",
    [
        ("enable_notifications", True),
        ("disable_notifications", False),
    ],
)
def test_toggle_notifications(webhook: Webhook, requests_mock, method, expected):
    toggle = getattr(webhook, method)
    m = requests_mock.post(webhook._url + "/enableNotifications")
    toggle()
    assert m.call_count == 1
    assert m.last_request.json() == {"enable": expected}


def test_extend_expiration(webhook: Webhook, requests_mock):
    m = requests_mock.post(
        webhook._url + "/refresh",
        json={"expirationTime": datetime.datetime.now().isoformat()},
    )
    webhook.extend_expiration()
    assert m.call_count == 1
    assert not m.last_request.text


def test_delete(webhook: Webhook, requests_mock):
    m = requests_mock.delete(webhook._url)
    webhook.delete()
    assert m.call_count == 1


def test_error_payload(payload_json):
    payload_json.update({"error": True, "code": "INVALID_HOOK"})
    payload = WebhookPayload.parse_obj(payload_json)
    assert payload.error is True
    assert payload.error_code == "INVALID_HOOK"


@pytest.mark.parametrize(
    "test_case",
    [
        # Basic test case for .payloads()
        {
            "count": 5,
            "chunksize": 5,
            "expect_numbers": [1, 2, 3, 4, 5],
            "expect_cursors": [1],
        },
        # Prevent regression of bug where payload.cursor always starts from 1
        {
            "count": 5,
            "chunksize": 5,
            "start_from": 20,
            "expect_numbers": [20, 21, 22, 23, 24],
            "expect_cursors": [20],
        },
        # Test that mightHaveMore controls when we stop iteration
        {
            "count": 8,
            "chunksize": 2,
            "extra_pages": 3,
            "expect_numbers": [1, 2, 3, 4, 5, 6, 7, 8],
            "expect_cursors": [1, 3, 5, 7],
        },
        # Test that .payloads(limit=n) stops iteration after n results.
        {
            "count": 5,
            "chunksize": 5,
            "start_from": 2,
            "payload_kwargs": {"limit": 3},
            "expect_numbers": [2, 3, 4],
            "expect_cursors": [2],
        },
    ],
)
def test_payloads(webhook: Webhook, requests_mock, payload_json, test_case):
    """
    Test that Webhook.payloads() continues to iterate payloads from the API
    until it reaches the point where mightHaveMore is false.
    """
    count = test_case["count"]
    chunksize = test_case["chunksize"]
    start = test_case.get("start_from", 1)
    extra_pages = test_case.get("extra_pages", 0)
    pagecount = math.ceil(count / chunksize)
    payload_pages = [
        [
            {**payload_json, "baseTransactionNumber": (m * chunksize) + n + start}
            for n in range(chunksize)
        ]
        for m in range(pagecount + extra_pages)
    ]
    mock_endpoint = requests_mock.get(
        webhook._url + "/payloads",
        response_list=[
            {
                "json": {
                    "cursor": page[-1]["baseTransactionNumber"] + 1,
                    "mightHaveMore": index < pagecount,  # extras should be ignored
                    "payloads": page,
                }
            }
            for index, page in enumerate(payload_pages, 1)
        ],
    )
    payload_kwargs = {"cursor": start, **test_case.get("payload_kwargs", {})}
    payloads = list(webhook.payloads(**payload_kwargs))
    # Ensure we got the right transactions in the right order.
    assert len(payloads) == len(test_case["expect_numbers"])
    assert [p.base_transaction_number for p in payloads] == test_case["expect_numbers"]
    assert [p.cursor for p in payloads] == test_case["expect_numbers"]
    # Ensure we sent the correct cursors, since requests_mock doesn't validate them.
    request_cursors = [req.qs["cursor"] for req in mock_endpoint.request_history]
    assert request_cursors == [[str(n)] for n in test_case["expect_cursors"]]


@pytest.mark.parametrize("argname", ["cursor", "limit"])
def test_payloads__invalid_args(webhook: Webhook, requests_mock, argname):
    with pytest.raises(ValueError):
        next(webhook.payloads(**{argname: 0}))


def test_payloads__stop_on_empty_list(webhook: Webhook, requests_mock, payload_json):
    """
    Test that an empty list causes us to not query for more, even if mightHaveMore is true.
    """
    requests_mock.get(
        webhook._url + "/payloads",
        response_list=[
            # we will retrieve this one...
            {"json": {"cursor": 2, "mightHaveMore": True, "payloads": [payload_json]}},
            # ...but should will stop here:
            {"json": {"cursor": 3, "mightHaveMore": True, "payloads": []}},
        ],
    )
    # this will cause an infinite loop if we don't check whether payloads is empty
    payloads = list(webhook.payloads())
    assert len(payloads) == 1


@pytest.mark.parametrize("secret", [b"secret-key", "c2VjcmV0LWtleQ=="])
def test_notification_from_request(secret):
    notification_json = {
        "base": {"id": "app00000000000000"},
        "webhook": {"id": "ach00000000000000"},
        "timestamp": "2022-02-01T21:25:05.663Z",
    }
    header = (
        "hmac-sha256-e26da696a90933647bddc83995c3e1e3bb1c3d8ce1ff61cb7469767d50b2b2d4"
    )

    body = json.dumps(notification_json)
    notification = WebhookNotification.from_request(body, header, secret)
    assert notification.base.id == "app00000000000000"
    assert notification.webhook.id == "ach00000000000000"
    assert notification.timestamp == "2022-02-01T21:25:05.663Z"

    with pytest.raises(ValueError):
        WebhookNotification.from_request("[1,2,3]", header, secret)
    with pytest.raises(ValueError):
        WebhookNotification.from_request(body, "bad-header", secret)
    with pytest.raises(ValueError):
        WebhookNotification.from_request(body, header, b"bad-secret")
    with pytest.raises(ValueError):
        WebhookNotification.from_request(body, header, "bad-secret")
