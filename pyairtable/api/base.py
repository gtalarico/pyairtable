from typing import List, Optional

from .abstract import ApiAbstract, TimeoutTuple
from .. import compat


class Base(ApiAbstract):
    """
    Represents an Airtable Base. This calss is similar to :class:`~pyairtable.api.Api`,
    except ``base_id`` is provided on init instead of provided on each method call.

    Usage:
        >>> base = Base('auth_token', 'base_id')
        >>> base.all()
    """

    base_id: str

    def __init__(
        self,
        api_key: str,
        base_id: str,
        *,
        timeout: Optional[TimeoutTuple] = None,
        retry_strategy: Optional["compat.Retry"] = None,
    ):
        """
        Args:
            api_key: |arg_api_key|
            base_id: |arg_base_id|

        Keyword Args:
            timeout (``Tuple``): |arg_timeout|
            retry_strategy (``Retry``): |arg_retry_strategy|
        """

        self.base_id = base_id
        super().__init__(api_key, timeout=timeout, retry_strategy=retry_strategy)

    def get_table(self, table_name: str) -> "Table":
        """
        Returns a new :class:`Table` instance using all shared
        attributes from :class:`Base`
        """
        return Table(self.api_key, self.base_id, table_name, timeout=self.timeout)

    def get_record_url(self, table_name: str, record_id: str):
        """
        Same as :meth:`Api.get_record_url <pyairtable.api.Api.get_record_url>`
        but without ``base_id`` arg.
        """
        return super()._get_record_url(self.base_id, table_name, record_id)

    def get(self, table_name: str, record_id: str):
        """
        Same as :meth:`Api.get <pyairtable.api.Api.get>`
        but without ``base_id`` arg.
        """
        return super()._get_record(self.base_id, table_name, record_id)

    def iterate(self, table_name: str, **options):
        """
        Same as :meth:`Api.iterate <pyairtable.api.Api.iterate>`
        but without ``base_id`` arg.
        """
        gen = super()._iterate(self.base_id, table_name, **options)
        for i in gen:
            yield i

    def first(self, table_name: str, **options):
        """
        Same as :meth:`Api.first <pyairtable.api.Api.first>`
        but without ``base_id`` arg.
        """
        return super()._first(self.base_id, table_name, **options)

    def all(self, table_name: str, **options):
        """
        Same as :meth:`Api.all <pyairtable.api.Api.all>`
        but without ``base_id`` arg.
        """
        return super()._all(self.base_id, table_name, **options)

    def create(self, table_name: str, fields: dict, typecast=False):
        """
        Same as :meth:`Api.create <pyairtable.api.Api.create>`
        but without ``base_id`` arg.
        """
        return super()._create(self.base_id, table_name, fields, typecast=typecast)

    def batch_create(self, table_name: str, records, typecast=False):
        """
        Same as :meth:`Api.batch_create <pyairtable.api.Api.batch_create>`
        but without ``base_id`` arg.
        """
        return super()._batch_create(
            self.base_id, table_name, records, typecast=typecast
        )

    def update(
        self,
        table_name: str,
        record_id: str,
        fields: dict,
        replace=False,
        typecast=False,
    ):
        """
        Same as :meth:`Api.update <pyairtable.api.Api.update>`
        but without ``base_id`` arg.
        """
        return super()._update(
            self.base_id,
            table_name,
            record_id,
            fields,
            replace=replace,
            typecast=typecast,
        )

    def batch_update(
        self, table_name: str, records: List[dict], replace=False, typecast=False
    ):
        """
        Same as :meth:`Api.batch_update <pyairtable.api.Api.batch_update>`
        but without ``base_id`` arg.
        """
        return super()._batch_update(
            self.base_id, table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, table_name: str, record_id: str):
        """
        Same as :meth:`Api.delete <pyairtable.api.Api.delete>`
        but without ``base_id`` arg.
        """
        return super()._delete(self.base_id, table_name, record_id)

    def batch_delete(self, table_name: str, record_ids: List[str]):
        """
        Same as :meth:`Api.batch_delete <pyairtable.api.Api.batch_delete>`
        but without ``base_id`` arg.
        """
        return super()._batch_delete(self.base_id, table_name, record_ids)

    def __repr__(self) -> str:
        return "<Airtable Base id={}>".format(self.base_id)

    def list_webhooks(self):
        """
        Returns webhooks associated with this base

        Returns:
            webhooks (``list``): List of Webhooks
        """
        return self._list_webhooks(self.base_id)
    
    def get_webhook(self, webhook_id: str):
        """
        Returns single webhook by ID
        Args:
            webhook_id: |arg_webhook_id|
        Returns:
            webhook: Webhook
        """
        return self._get_webhook(self.base_id, webhook_id)

    def create_webhook(self, specification: dict, notificationUrl = None):
        """
        Creates a new webhook with passed specifications and posting to the optional notificationUrl

        Usage:
        >>> base = Base(api_key)
        >>> base.create_webhook({
                "options": {
                    "filters": {
                        "dataTypes": ['tableData']
                    }
                }
        ... }) 

        Args:
            specification: |arg_specification|
            webhook_id: |arg_notificationUrl|
        """
        return self._create_webhook(self.base_id, specification, notificationUrl)
    
    def delete_webhook(self, webhook_id: str):
        """
        Deletes the webhook with passed webhook ID

        Args:
            webhook_id: |arg_webhook_id|
        """
        return self._delete_webhook(self.base_id, webhook_id)
    
    def toggle_notifications(self, webhook_id: str, enabled: bool):
        """
        Enables or disable notifications for the webhook with the passed webhook ID.
        
        Args:
            webhook_id: |arg_webhook_id|
            enabled: |arg_enabled|
        """
        return self._toggle_notifications_webhook(self.base_id, webhook_id, enabled)
    
    def refresh_webhook(self, webhook_id: str):
        """
        Extends the life of the webhook by 7 days from current date/time.

        Args:
            webhook_id: |arg_webhook_id|
        """
        return self._refresh_webhook(self.base_id, webhook_id)
    
    def get_payloads(self, webhook_id: str, cursor=1, limit=50):
        """
        Retrieves notifications/posts to the webhook, with a maximum of 50 returned at a time. 
        The cursor can be used to iterate over all payloads by storing the next cursor returned by this function.

        Args:
            webhook_id: |arg_webhook_id|
            cursor: |arg_cursor|
            limit: |arg_limit|

        Returns:
            payloads (``list``): List of Webhook Notifications
        """
        return self._payloads_webhook(self.base_id, webhook_id, cursor, limit)
    
from .table import Table  # noqa