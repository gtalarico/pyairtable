from typing import Dict, Iterable, List, Optional

from pyairtable.models.schema import EnterpriseInfo, UserGroup, UserInfo
from pyairtable.utils import cache_unless_forced, enterprise_only, is_user_id


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

    def group(self, group_id: str) -> UserGroup:
        url = self.api.build_url(f"meta/groups/{group_id}")
        return UserGroup.parse_obj(self.api.request("GET", url))

    def user(self, id_or_email: str) -> UserInfo:
        """
        Retrieve information on a single user with the given ID or email.

        Args:
            id_or_email: A user ID (``usrQBq2RGdihxl3vU``) or email address.
        """
        return self.users([id_or_email])[0]

    def users(self, ids_or_emails: Iterable[str]) -> List[UserInfo]:
        """
        Retrieve information on the users with the given IDs or emails.

        Following the Airtable API specification, pyAirtable will perform
        one API request for each user ID. However, when given a list of emails,
        pyAirtable only needs to perform one API request for the entire list.

        Read more at `Get user by ID <https://airtable.com/developers/web/api/get-user-by-id>`__
        and `Get user by email <https://airtable.com/developers/web/api/get-user-by-email>`__.

        Args:
            ids_or_emails: A sequence of user IDs (``usrQBq2RGdihxl3vU``)
                or email addresses (or both).
        """
        users: Dict[str, UserInfo] = {}  # key by user ID to avoid returning duplicates
        user_ids: List[str] = []
        emails: List[str] = []
        for value in ids_or_emails:
            if "@" in value:
                emails.append(value)
            elif is_user_id(value):
                user_ids.append(value)
            else:
                raise ValueError(f"unrecognized user ID or email: {value!r}")

        for user_id in user_ids:
            response = self.api.request("GET", f"{self.url}/users/{user_id}")
            info = UserInfo.parse_obj(response)
            users[info.id] = info

        if emails:
            params = {"email": emails}
            response = self.api.request("GET", f"{self.url}/users", params=params)
            users.update(
                {
                    info.id: info
                    for user_obj in response["users"]
                    if (info := UserInfo.parse_obj(user_obj))
                }
            )

        return list(users.values())


# These are at the bottom of the module to avoid circular imports
import pyairtable.api.api  # noqa
import pyairtable.api.base  # noqa
