import pytest

from pyairtable import Base, Table

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def delete_webhooks_after_itest(base):
    """
    Ensure that we always delete webhooks, even if a test fails.
    """
    try:
        yield
    finally:
        for webhook in base.webhooks():
            webhook.delete()


def test_webhook(base: Base, table: Table, table_id, cols):
    result = base.add_webhook(
        # Throwaway URL; there's no way for us to reliably capture these in a test
        "https://example.com/",
        {
            "options": {
                "filters": {
                    "dataTypes": ["tableData"],
                }
            }
        },
    )
    # Retrieve the webhook and disable it immediately,
    # so we don't actually hit example.com with data.
    webhook_id = result.id
    webhook = base.webhook(webhook_id)
    webhook.disable_notifications()

    # Trigger the webhook once
    created = table.create({cols.TEXT: "Hey there!"})
    # Get all payloads from the webhook; there should only be one
    payloads = list(webhook.payloads())
    payload = payloads[0]
    assert len(payloads) == 1
    # Validate that the webhook payload includes the first change we made
    table_changed = payload.changed_tables_by_id[table_id]
    record_created = table_changed.created_records_by_id[created["id"]]
    assert record_created.cell_values_by_field_id == {cols.TEXT_ID: "Hey there!"}

    # Trigger the webhook many times
    count = 20
    for index in range(count):
        table.update(created["id"], {cols.TEXT: str(index)})
    # Get all remaining payloads from the webhook endpoint.
    # This is the only place (today) where we test WebhookPayload.cursor
    payloads = list(webhook.payloads(cursor=(payload.cursor + 1)))
    assert len(payloads) == count
    # Validate the payload values
    assert list(range(count)) == [
        int(record_changed.current.cell_values_by_field_id[cols.TEXT_ID])
        for payload in payloads
        if (table_changed := payload.changed_tables_by_id[table_id])
        and (record_changed := table_changed.changed_records_by_id[created["id"]])
    ]
