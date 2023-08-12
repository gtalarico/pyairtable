from typing import Iterable, List, Optional

from pyairtable.models.schema import EnterpriseInfo, GroupInfo, UserInfo
from pyairtable.utils import enterprise_only


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

    def info(self, *, force: bool = False) -> EnterpriseInfo:
        """
        Retrieves basic information about the enterprise, caching the result.

        Args:
            force: |kwarg_force_metadata|
        """
        if force or not self._info:
            params = {"include": ["collaborators", "inviteLinks"]}
            payload = self.api.request("GET", self.url, params=params)
            self._info = EnterpriseInfo.parse_obj(payload)
        return self._info

    def group(self, group_id: str) -> GroupInfo:
        url = self.api.build_url(f"meta/groups/{group_id}")
        return GroupInfo.parse_obj(self.api.request("GET", url))

    def user(self, id_or_email: str) -> UserInfo:
        """
        Returns information on a single user with the given ID or email.

        Args:
            id_or_email: A user ID (``usrQBq2RGdihxl3vU``) or email address.
        """
        return self.users([id_or_email])[0]

    def users(self, ids_or_emails: Iterable[str]) -> List[UserInfo]:
        """
        Returns information on the users with the given IDs or emails.

        Args:
            ids_or_emails: A sequence of user IDs (``usrQBq2RGdihxl3vU``)
                or email addresses (or both).
        """
        user_ids: List[str] = []
        emails: List[str] = []
        for value in ids_or_emails:
            (user_ids, emails)["@" in value].append(value)

        users = []
        for user_id in user_ids:
            response = self.api.request("GET", f"{self.url}/users/{user_id}")
            users.append(UserInfo.parse_obj(response))
        if emails:
            response = self.api.request(
                "GET", f"{self.url}/users", params={"email": emails}
            )
            users += [UserInfo.parse_obj(user_obj) for user_obj in response["users"]]

        return users


# These are at the bottom of the module to avoid circular imports
import pyairtable.api.api  # noqa
import pyairtable.api.base  # noqa
