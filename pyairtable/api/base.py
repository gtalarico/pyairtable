import warnings
from functools import lru_cache
from typing import Any, Dict, List, Union

import pyairtable.api.api
import pyairtable.api.table
from pyairtable.models.webhook import (
    CreateWebhook,
    CreateWebhookResponse,
    Webhook,
    WebhookSpecification,
)


class Base:
    """
    Represents an Airtable base.
    """

    #: The connection to the Airtable API.
    api: "pyairtable.api.api.Api"

    #: The base ID, in the format ``appXXXXXXXXXXXXXX``
    id: str

    def __init__(self, api: Union["pyairtable.api.api.Api", str], base_id: str):
        """
        Old style constructor takes ``str`` arguments, and will create its own
        instance of :class:`Api`.

        This approach is deprecated, and will likely be removed in the future.

            >>> Base("access_token", "base_id")

        New style constructor takes an instance of :class:`Api`:

            >>> Base(api, "table_name")

        Args:
            api: An instance of :class:`Api` or an Airtable access token.
            base_id: |arg_base_id|
        """
        if isinstance(api, str):
            warnings.warn(
                "Passing API keys to pyairtable.Base is deprecated; use Api.base() instead."
                " See https://pyairtable.rtfd.org/en/latest/migrations.html for details.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            api = pyairtable.api.api.Api(api)

        self.api = api
        self.id = base_id

    def __repr__(self) -> str:
        return f"<pyairtable.Base base_id={self.id!r}>"

    @lru_cache
    def table(self, table_name: str) -> "pyairtable.api.table.Table":
        """
        Returns a new :class:`Table` instance using all shared
        attributes from :class:`Base`.

        Args:
            table_name: An Airtable table name. Table name should be unencoded,
                as shown on browser.
        """
        return pyairtable.api.table.Table(None, self, table_name)

    @property
    def url(self) -> str:
        return self.api.build_url(self.id)

    @property
    def webhooks_url(self) -> str:
        return self.api.build_url("bases", self.id, "webhooks")

    def webhooks(self) -> List[Webhook]:
        """
        Retrieves all the base's webhooks from the API
        (see: `List webhooks <https://airtable.com/developers/web/api/list-webhooks>`_).

        Usage:
            >>> base.webhooks()
            [
                Webhook(
                    id='ach00000000000001',
                    are_notifications_enabled=True,
                    cursor_for_next_payload=1,
                    is_hook_enabled=True,
                    last_successful_notification_time=None,
                    notification_url="https://example.com",
                    last_notification_result=None,
                    expiration_time="2023-07-01T00:00:00.000Z",
                    specification: WebhookSpecification(...)
                )
            ]
        """
        response = self.api.request("GET", self.webhooks_url)
        return [
            Webhook.from_api(
                api=self.api,
                url=f"{self.webhooks_url}/{data['id']}",
                obj=data,
            )
            for data in response["webhooks"]
        ]

    def webhook(self, webhook_id: str) -> Webhook:
        """
        Returns a single webhook or raises ``KeyError`` if the given ID is invalid.

        Airtable's API does not permit retrieving a single webhook, so this function
        will call :meth:`~webhooks` and simply return one item from the list.
        """
        for webhook in self.webhooks():
            if webhook.id == webhook_id:
                return webhook
        raise KeyError(f"webhook not found: {webhook_id!r}")

    def add_webhook(
        self,
        notify_url: str,
        spec: Union[WebhookSpecification, Dict[Any, Any]],
    ) -> CreateWebhookResponse:
        """
        Creates a webhook on the base with the given
        `webhooks specification <https://airtable.com/developers/web/api/model/webhooks-specification>`_.

        The return value will contain a unique secret that must be saved
        in order to validate payloads as they are sent to your notification
        endpoint. If you do not save this, you will have no way of confirming
        that payloads you receive did, in fact, come from Airtable.

        For more on how to validate notifications to your webhook, see
        :meth:`WebhookNotification.from_request() <pyairtable.models.WebhookNotification.from_request>`.

        Usage:
            >>> base.add_webhook(
            ...     "https://example.com",
            ...     {
            ...         "options": {
            ...             "filters": {
            ...                 "dataTypes": ["tableData"],
            ...             }
            ...         }
            ...     }
            ... )
            CreateWebhookResponse(
                id='ach00000000000001',
                mac_secret_base64='c3VwZXIgZHVwZXIgc2VjcmV0',
                expiration_time='2023-07-01T00:00:00.000Z'
            )

        Raises:
            pydantic.ValidationError: If the dict provided is invalid.

        Args:
            notify_url: The URL where Airtable will POST all event notifications.
            spec: The configuration for the webhook. It is easiest to pass a dict
                that conforms to the `webhooks specification`_ but you
                can also provide :class:`~pyairtable.models.webhook.WebhookSpecification`.
        """
        if isinstance(spec, dict):
            spec = WebhookSpecification.parse_obj(spec)

        create = CreateWebhook(notification_url=notify_url, specification=spec)
        request = create.dict(by_alias=True, exclude_unset=True)
        response = self.api.request("POST", self.webhooks_url, json=request)
        return CreateWebhookResponse.parse_obj(response)
