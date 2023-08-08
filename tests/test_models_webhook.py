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


def test_payloads(webhook: Webhook, requests_mock, payload_json):
    """
    Test that Webhook.payloads() continues to iterate payloads from the API
    until it reaches the point where mightHaveMore is false.
    """
    count = 8
    chunksize = 2
    pagecount = math.ceil(count / chunksize) + 1  # one extra page, to be ignored
    payload_pages = [
        [
            {**payload_json, "baseTransactionNumber": (m * chunksize) + n + 1}
            for n in range(chunksize)
        ]
        for m in range(pagecount)
    ]
    mock_endpoint = requests_mock.get(
        webhook._url + "/payloads",
        response_list=[
            {
                "json": {
                    "cursor": page[-1]["baseTransactionNumber"] + 1,
                    "mightHaveMore": index < pagecount - 1,  # extras should be ignored
                    "payloads": page,
                }
            }
            for index, page in enumerate(payload_pages, 1)
        ],
    )
    # Ensure we got the right transactions in the right order.
    payloads = list(webhook.payloads())
    assert len(payloads) == count
    assert [p.base_transaction_number for p in payloads] == [1, 2, 3, 4, 5, 6, 7, 8]
    assert [p.cursor for p in payloads] == [1, 2, 3, 4, 5, 6, 7, 8]
    # Ensure we sent the correct cursors, since requests_mock doesn't validate them.
    request_cursors = [req.qs["cursor"] for req in mock_endpoint.request_history]
    assert request_cursors == [["1"], ["3"], ["5"], ["7"]]


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
