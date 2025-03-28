.. include:: _substitutions.rst
.. include:: _warn_latest.rst

Webhooks
==============================

Airtable's `Webhooks API <https://airtable.com/developers/web/api/webhooks-overview>`_
provides a flexible way to receive real-time notifications about changes to Airtable
records and metadata. This is useful for keeping external applications in sync with
Airtable data or triggering workflows based on record updates.

Using **pyAirtable**, you can easily create and manage webhooks, as well as retrieve
webhook payloads, through the :class:`~pyairtable.Base` class.

Setting Up a Webhook
--------------------

To set up a webhook, use the :meth:`~pyairtable.Base.add_webhook` method. This allows
you to register a webhook for a specific base and table.

Example: Creating a Webhook
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pyairtable import Base

    base = Base("YOUR_API_KEY", "YOUR_BASE_ID")
    webhook = base.add_webhook(
        table_id="tblXXXXXX",
        notification_url="https://your-webhook-endpoint.com",
        webhook_scope="table"
    )
    print(webhook)

Retrieving Webhooks
-------------------

You can list all active webhooks for a base using :meth:`~pyairtable.Base.webhooks`.

.. code-block:: python

    webhooks = base.webhooks()
    for webhook in webhooks:
        print(webhook["id"], webhook["notificationUrl"])

Fetching Webhook Details
------------------------

To retrieve details about a specific webhook, use :meth:`~pyairtable.Base.webhook`.

.. code-block:: python

    webhook_id = "whkXXXXXX"
    details = base.webhook(webhook_id)
    print(details)

Handling Webhook Payloads
-------------------------

When Airtable triggers a webhook, it sends a `POST` request with a JSON payload. You
can inspect webhook payloads using :meth:`~pyairtable.models.Webhook.payloads`.

Example Payload
^^^^^^^^^^^^^^^

.. code-block:: json

    {
      "timestamp": "2023-03-16T12:34:56.789Z",
      "change": {
        "tableId": "tblXXXXXX",
        "recordId": "recYYYYYY",
        "action": "update"
      }
    }

Testing Webhooks
----------------

To test your webhook setup, you can use tools like:

- **`Beeceptor <https://beeceptor.com/>`_** – Set up a mock endpoint to inspect webhook payloads.
- **`Pipedream RequestBin <https://pipedream.com/requestbin>`_** – Capture and analyze webhook requests.
