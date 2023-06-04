import posixpath
from functools import lru_cache
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple, TypeVar, Union

import requests
from requests.sessions import Session
from typing_extensions import TypeAlias

import pyairtable.api.base
import pyairtable.api.table
from pyairtable.api import retrying
from pyairtable.api.params import options_to_json_and_params, options_to_params
from pyairtable.api.types import UserAndScopesDict, assert_typed_dict
from pyairtable.utils import chunked

T = TypeVar("T")
TimeoutTuple: TypeAlias = Tuple[int, int]


class Api:
    """
    Represents an Airtable API. Implements basic URL construction,
    session and request management, and retrying logic.

    Usage:
        >>> api = Api('auth_token')
        >>> api.all('base_id', 'table_name')
    """

    VERSION = "v0"
    API_LIMIT = 1.0 / 5  # 5 per second

    #: Airtable-imposed limit on number of records per batch create/update operation.
    MAX_RECORDS_PER_REQUEST = 10

    #: Airtable-imposed limit on the length of a URL (including query parameters).
    MAX_URL_LENGTH = 16000

    def __init__(
        self,
        api_key: str,
        *,
        timeout: Optional[TimeoutTuple] = None,
        retry_strategy: Optional[Union[bool, retrying.Retry]] = True,
        endpoint_url: str = "https://api.airtable.com",
    ):
        """
        Args:
            api_key: An Airtable API key or personal access token.
            timeout: A tuple indicating a connect and read timeout.
                e.g. ``timeout=(2,5)`` would configure a 2 second timeout for
                the connection to be established  and 5 seconds for a
                server read timeout. Default is ``None`` (no timeout).
            retry_strategy: An instance of
                `urllib3.util.Retry <https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry>`_.
                If ``None`` or ``False``, requests will not be retried.
                If ``True``, the default strategy will be applied
                (see :func:`~pyairtable.retry_strategy` for details).
            endpoint_url: The API endpoint to use. Override this if you are using
                a debugging or caching proxy.
        """
        if retry_strategy is True:
            retry_strategy = retrying.retry_strategy()
        if not retry_strategy:
            self.session = Session()
        else:
            self.session = retrying._RetryingSession(retry_strategy)

        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.api_key = api_key

    @property
    def api_key(self) -> str:
        """
        Airtable API key or access token to use on all connections.
        """
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.session.headers.update({"Authorization": "Bearer {}".format(value)})
        self._api_key = value

    def __repr__(self) -> str:
        return "<pyairtable.Api>"

    @lru_cache
    def base(self, base_id: str) -> "pyairtable.api.base.Base":
        """
        Returns a new :class:`Base` instance that uses this instance of :class:`Api`.
        """
        return pyairtable.api.base.Base(self, base_id)

    def table(self, base_id: str, table_name: str) -> "pyairtable.api.table.Table":
        """
        Returns a new :class:`Table` instance that uses this instance of :class:`Api`.
        """
        return self.base(base_id).table(table_name)

    def build_url(self, *components: str) -> str:
        """
        Returns a URL to the Airtable API endpoint with the given URL components,
        including the API version number.
        """
        return posixpath.join(self.endpoint_url, self.VERSION, *components)

    def request(
        self,
        method: str,
        url: str,
        fallback: Optional[Tuple[str, str]] = None,
        options: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Makes a request to the Airtable API, optionally converting a GET to a POST
        if the URL exceeds the API's maximum URL length.

        See https://support.airtable.com/docs/enforcement-of-url-length-limit-for-web-api-requests

        Args:
            method: HTTP method to use.
            url: The URL we're attempting to call.
            fallback: The method and URL to use if we have to convert a GET to a POST.
            options: Airtable-specific query params to use while fetching records.
                See :ref:`Parameters` for valid options.
            params: Additional query params to append to the URL as-is.
            json: The JSON payload for a POST/PUT/PATCH/DELETE request.
        """
        # Convert Airtable-specific options to query params, but give priority to query params
        # that are explicitly passed via `params=`. This is to preserve backwards-compatibility for
        # any library users who might be calling `self._request` directly.
        request_params = {
            **options_to_params(options or {}),
            **(params or {}),
        }

        # Build a requests.PreparedRequest so we can examine how long the URL is.
        prepared = self.session.prepare_request(
            requests.Request(
                method,
                url=url,
                params=request_params,
                json=json,
            )
        )

        # If our URL is too long, move *most* (not all) query params into a POST body.
        if (
            fallback
            and method.upper() == "GET"
            and len(str(prepared.url)) >= self.MAX_URL_LENGTH
        ):
            json, spare_params = options_to_json_and_params(options or {})
            return self.request(
                method=fallback[0],
                url=fallback[1],
                params={**spare_params, **(params or {})},
                json=json,
            )

        response = self.session.send(prepared, timeout=self.timeout)
        return self._process_response(response)

    def _process_response(self, response: requests.Response) -> Any:
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            err_msg = str(exc)

            # Attempt to get Error message from response, Issue #16
            try:
                error_dict = response.json()
            except ValueError:
                pass
            else:
                if "error" in error_dict:
                    err_msg += " [Error: {}]".format(error_dict["error"])
            exc.args = (*exc.args, err_msg)
            raise exc
        else:
            return response.json()

    def chunked(self, iterable: Sequence[T]) -> Iterator[Sequence[T]]:
        """
        Iterates through chunks of the given sequence that are equal in size
        to the maximum number of records per request allowed by the API.
        """
        return chunked(iterable, self.MAX_RECORDS_PER_REQUEST)

    def whoami(self) -> UserAndScopesDict:
        """
        Return the current user ID and (if connected via OAuth) the list of scopes.
        See `Get user ID & scopes <https://airtable.com/developers/web/api/get-user-id-scopes>`_ for more information.
        """
        data = self.request("GET", self.build_url("meta/whoami"))
        return assert_typed_dict(UserAndScopesDict, data)
