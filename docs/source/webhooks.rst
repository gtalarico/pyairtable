.. include:: _substitutions.rst
.. include:: _warn_latest.rst

Webhooks
==============================

Airtable's `Webhooks API <https://airtable.com/developers/web/api/webhooks-overview>`_
offers a configurable and flexible way to receive programmatic notifications of
changes to Airtable data and metadata.

The basic flow for webhooks is:

1. Use :meth:`Base.add_webhook <pyairtable.Base.add_webhook>` to create a webhook.
2. Airtable will ``POST`` notifications to the webhook URL you provided.
3. Use :meth:`WebhookNotification.from_request <pyairtable.models.WebhookNotification.from_request>` to validate each notification.
4. Use :meth:`Webhook.payloads <pyairtable.models.Webhook.payloads>` to retrieve new payloads after the notification.

This means it is technically possible to ignore webhook notifications altogether and to simply
poll a webhook periodically for new payloads. However, this increases the likelihood of running into
`Airtable's API rate limits <https://airtable.com/developers/web/api/rate-limits>`__.

When using webhooks, you need some way to persist the ``cursor`` of the webhook
payload, so that you do not retrieve the same payloads again on subsequent calls,
even if your job is interrupted in the middle of processing a list of payloads.

For example:

    .. code-block:: python

        from flask import Flask, request
        from pyairtable import Api
        from pyairtable.models import WebhookNotification

        app = Flask(__name__)

        @app.route("/airtable-webhook", methods=["POST"])
        def airtable_webhook():
            body = request.data
            header = request.headers["X-Airtable-Content-MAC"]
            secret = app.config["AIRTABLE_WEBHOOK_SECRET"]
            event = WebhookNotification.from_request(body, header, secret)
            airtable = Api(app.config["AIRTABLE_API_KEY"])
            webhook = airtable.base(event.base.id).webhook(event.webhook.id)
            cursor = int(your_database.get(event.webhook, 0)) + 1

            for payload in webhook.payloads(cursor=cursor):
                process_payload(payload)  # probably enqueue a background job
                your_database.set(event.webhook, payload.cursor + 1)

            return ("", 204)  # intentionally empty response

Methods
-------

The following methods will be most commonly used for working with payloads.
You can read the full documentation at :mod:`pyairtable.models.webhook`.

.. automethod:: pyairtable.Base.add_webhook
    :noindex:

.. automethod:: pyairtable.Base.webhooks
    :noindex:

.. automethod:: pyairtable.Base.webhook
    :noindex:

.. automethod:: pyairtable.models.WebhookNotification.from_request
    :noindex:

.. automethod:: pyairtable.models.Webhook.payloads
    :noindex:
