from typing import Iterable, List, Optional

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


# These are at the bottom of the module to avoid circular imports
import pyairtable.api.api  # noqa
import pyairtable.api.base  # noqa
