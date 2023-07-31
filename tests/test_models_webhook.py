import datetime
from operator import attrgetter

import pytest

import pyairtable.models.webhook
from pyairtable.models.webhook import Webhook, WebhookPayload


@pytest.fixture
def webhook(sample_json, base, api):
    webhook_json = sample_json("Webhook")
    return Webhook.from_api(
        api=api,
        url=f"{base.webhooks_url}/{webhook_json['id']}",
        obj=webhook_json,
    )


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


def test_error_payload(sample_json):
    payload_json = sample_json("WebhookPayload")
    payload_json.update({"error": True, "code": "INVALID_HOOK"})
    payload = WebhookPayload.parse_obj(payload_json)
    assert payload.error is True
    assert payload.error_code == "INVALID_HOOK"


def test_payloads(webhook: Webhook, requests_mock, sample_json):
    """
    Test that Webhook.payloads() continues to iterate payloads from the API
    until it reaches the point where mightHaveMore is false.
    """
    count = extra = 5
    payloads_json = [
        {**sample_json("WebhookPayload"), "baseTransactionNumber": n}
        for n in range(count + extra)
    ]
    requests_mock.get(
        webhook._url + "/payloads",
        response_list=[
            {
                "json": {
                    "cursor": index + 1,
                    "mightHaveMore": index < count,  # extras should be ignored
                    "payloads": [payload],
                }
            }
            for index, payload in enumerate(payloads_json, 1)
        ],
    )
    payloads = list(webhook.payloads())
    assert len(payloads) == count
    assert [p.base_transaction_number for p in payloads] == [0, 1, 2, 3, 4]


def test_payloads__stop_on_empty_list(webhook: Webhook, requests_mock, sample_json):
    """
    Test that an empty list causes us to not query for more, even if mightHaveMore is true.
    """
    payload_json = sample_json("WebhookPayload")
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
