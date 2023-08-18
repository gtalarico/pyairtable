Webhooks
==============================

Airtable's `Webhooks API <https://airtable.com/developers/web/api/webhooks-overview>`_
offers a configurable and flexible way to receive programmatic notifications of
changes to Airtable data and metadata.

pyAirtable allows you to create and manage webhooks and to retrieve webhook payloads
using a straightforward API within the :class:`~pyairtable.Base` class.

.. automethod:: pyairtable.Base.add_webhook
    :noindex:

.. automethod:: pyairtable.Base.webhooks
    :noindex:

.. automethod:: pyairtable.Base.webhook
    :noindex:

.. automethod:: pyairtable.models.Webhook.payloads
    :noindex:

.. autoclass:: pyairtable.models.WebhookNotification
    :noindex:
    :members: from_request
