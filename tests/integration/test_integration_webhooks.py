import pytest

from pyairtable import Base, Table


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
    # Trigger the webhook
    created = table.create({cols.TEXT: "Hey there!"})
    # Retrieve the webhook and disable it immediately
    webhook_id = result.id
    webhook = base.webhook(webhook_id)
    webhook.disable_notifications()
    # Get all payloads from the webhook; there should only be one
    payloads = list(webhook.payloads())
    payload = payloads[0]
    assert len(payloads) == 1
    # Validate that the webhook payload includes the change we made
    table_changes = payload.changed_tables_by_id[table_id]
    record_changes = table_changes.created_records_by_id[created["id"]]
    assert record_changes.cell_values_by_field_id == {cols.TEXT_ID: "Hey there!"}
