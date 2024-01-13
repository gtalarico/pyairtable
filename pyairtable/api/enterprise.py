import datetime
from typing import Any, Iterable, Iterator, List, Optional, Union, cast

from typing_extensions import TypeVar

from pyairtable.models.audit import AuditLogResponse
from pyairtable.models.schema import EnterpriseInfo, UserGroup, UserInfo
from pyairtable.utils import cache_unless_forced, enterprise_only


@enterprise_only
class Enterprise:
    """
    Represents an Airtable enterprise account.

    >>> enterprise = api.enterprise("entUBq2RGdihxl3vU")
    >>> enterprise.info().workspace_ids
    ['wspmhESAta6clCCwF', ...]
    """

    def __init__(self, api: "pyairtable.api.api.Api", workspace_id: str):
        self.api = api
        self.id = workspace_id
        self._info: Optional[EnterpriseInfo] = None

    @property
    def url(self) -> str:
        return self.api.build_url("meta/enterpriseAccounts", self.id)

    @cache_unless_forced
    def info(self) -> EnterpriseInfo:
        """
        Retrieve basic information about the enterprise, caching the result.
        """
        params = {"include": ["collaborators", "inviteLinks"]}
        payload = self.api.request("GET", self.url, params=params)
        return EnterpriseInfo.parse_obj(payload)

    def group(self, group_id: str, collaborations: bool = True) -> UserGroup:
        """
        Retrieve information on a single user group with the given ID.

        Args:
            group_id: A user group ID (``grpQBq2RGdihxl3vU``).
            collaborations: If ``False``, no collaboration data will be requested
                from Airtable. This may result in faster responses.
        """
        params = {"include": ["collaborations"] if collaborations else []}
        url = self.api.build_url(f"meta/groups/{group_id}")
        payload = self.api.request("GET", url, params=params)
        return UserGroup.parse_obj(payload)

    def user(self, id_or_email: str, collaborations: bool = True) -> UserInfo:
        """
        Retrieve information on a single user with the given ID or email.

        Args:
            id_or_email: A user ID (``usrQBq2RGdihxl3vU``) or email address.
            collaborations: If ``False``, no collaboration data will be requested
                from Airtable. This may result in faster responses.
        """
        return self.users([id_or_email], collaborations=collaborations)[0]

    def users(
        self,
        ids_or_emails: Iterable[str],
        collaborations: bool = True,
    ) -> List[UserInfo]:
        """
        Retrieve information on the users with the given IDs or emails.

        Read more at `Get users by ID or email <https://airtable.com/developers/web/api/get-users-by-id-or-email>`__.

        Args:
            ids_or_emails: A sequence of user IDs (``usrQBq2RGdihxl3vU``)
                or email addresses (or both).
            collaborations: If ``False``, no collaboration data will be requested
                from Airtable. This may result in faster responses.
        """
        user_ids: List[str] = []
        emails: List[str] = []
        for value in ids_or_emails:
            (emails if "@" in value else user_ids).append(value)

        response = self.api.request(
            method="GET",
            url=f"{self.url}/users",
            params={
                "id": user_ids,
                "email": emails,
                "include": ["collaborations"] if collaborations else [],
            },
        )
        # key by user ID to avoid returning duplicates
        users = {
            info.id: info
            for user_obj in response["users"]
            if (info := UserInfo.from_api(user_obj, self.api, context=self))
        }
        return list(users.values())

    def audit_log(
        self,
        *,
        page_size: Optional[int] = None,
        page_limit: Optional[int] = None,
        sort_asc: Optional[bool] = False,
        previous: Optional[str] = None,
        next: Optional[str] = None,
        start_time: Optional[Union[str, datetime.date, datetime.datetime]] = None,
        end_time: Optional[Union[str, datetime.date, datetime.datetime]] = None,
        user_id: Optional[Union[str, Iterable[str]]] = None,
        event_type: Optional[Union[str, Iterable[str]]] = None,
        model_id: Optional[Union[str, Iterable[str]]] = None,
        category: Optional[Union[str, Iterable[str]]] = None,
    ) -> Iterator[AuditLogResponse]:
        """
        Retrieve and yield results from the `Audit Log <https://airtable.com/developers/web/api/audit-logs-integration-guide>`__,
        one page of results at a time. Each result is an instance of :class:`~pyairtable.models.audit.AuditLogResponse`
        and contains the pagination IDs returned from the API, as described in the linked documentation.

        By default, the Airtable API will return up to 180 days of audit log events, going backwards from most recent.
        Retrieving all records may take some time, but is as straightforward as:

            >>> enterprise = Enterprise("entYourEnterpriseId")
            >>> events = [
            ...     event
            ...     for page in enterprise.audit_log()
            ...     for event in page.events
            ... ]

        If you are creating a record of all audit log events, you probably want to start with the earliest
        events in the retention window and iterate chronologically. You'll likely have a job running
        periodically in the background, so you'll need some way to persist the pagination IDs retrieved
        from the API in case that job is interrupted and needs to be restarted.

        The sample code below will use a local file to remember the next page's ID, so that if the job is
        interrupted, it will resume where it left off (potentially processing some entries twice).

        .. code-block:: python

            import os
            import shelve
            import pyairtable

            def handle_event(event):
                print(event)

            api = pyairtable.Api(os.environ["AIRTABLE_API_KEY"])
            enterprise = api.enterprise(os.environ["AIRTABLE_ENTERPRISE_ID"])
            persistence = shelve.open("audit_log.db")
            first_page = persistence.get("next", None)

            for page in enterprise.audit_log(sort_asc=True, next=first_page):
                for event in page.events:
                    handle_event(event)
                persistence["next"] = page.pagination.next

        For more information on any of the keyword parameters below, refer to the
        `audit log events <https://airtable.com/developers/web/api/audit-log-events>`__
        API documentation.

        Args:
            page_size: How many events per page to return (maximum 100).
            page_limit: How many pages to return before stopping.
            sort_asc: Whether to sort in ascending order (earliest to latest)
                rather than descending order (latest to earliest).
            previous: Requests the previous page of results from the given ID.
                See the `audit log integration guide <https://airtable.com/developers/web/api/audit-logs-integration-guide>`__
                for more information on pagination parameters.
            next: Requests the next page of results according to the given ID.
                See the `audit log integration guide <https://airtable.com/developers/web/api/audit-logs-integration-guide>`__
                for more information on pagination parameters.
            start_time: Earliest timestamp to retrieve (inclusive).
            end_time: Latest timestamp to retrieve (inclusive).
            originating_user_id: Retrieve audit log events originating
                from the provided user ID or IDs (maximum 100).
            event_type: Retrieve audit log events falling under the provided
                `audit log event type <https://airtable.com/developers/web/api/audit-log-event-types>`__
                or types (maximum 100).
            model_id: Retrieve audit log events taking action on, or involving,
                the provided model ID or IDs (maximum 100).
            category: Retrieve audit log events belonging to the provided
                audit log event category or categories.

        Returns:
            An object representing a single page of audit log results.
        """

        start_time = _coerce_isoformat(start_time)
        end_time = _coerce_isoformat(end_time)
        user_id = _coerce_list(user_id)
        event_type = _coerce_list(event_type)
        model_id = _coerce_list(model_id)
        category = _coerce_list(category)
        params = {
            "startTime": start_time,
            "endTime": end_time,
            "originatingUserId": user_id,
            "eventType": event_type,
            "modelId": model_id,
            "category": category,
            "pageSize": page_size,
            "sortOrder": ("ascending" if sort_asc else "descending"),
            "previous": previous,
            "next": next,
        }
        params = {k: v for (k, v) in params.items() if v}
        offset_field = "next" if sort_asc else "previous"
        url = self.api.build_url(f"meta/enterpriseAccounts/{self.id}/auditLogEvents")
        iter_requests = self.api.iterate_requests(
            method="GET",
            url=url,
            params=params,
            offset_field=offset_field,
        )
        for count, response in enumerate(iter_requests, start=1):
            parsed = AuditLogResponse.parse_obj(response)
            yield parsed
            if not parsed.events:
                return
            if page_limit is not None and count >= page_limit:
                return


def _coerce_isoformat(value: Any) -> Optional[str]:
    if value is None:
        return value
    if isinstance(value, str):
        datetime.datetime.fromisoformat(value)  # validates type, nothing more
        return value
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    raise TypeError(f"cannot coerce {type(value)} into ISO 8601 str")


T = TypeVar("T")


def _coerce_list(value: Optional[Union[str, Iterable[T]]]) -> List[T]:
    if value is None:
        return []
    if isinstance(value, str):
        return cast(List[T], [value])
    return list(value)


# These are at the bottom of the module to avoid circular imports
import pyairtable.api.api  # noqa
import pyairtable.api.base  # noqa
