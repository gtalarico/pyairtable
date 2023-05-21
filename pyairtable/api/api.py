import posixpath
import time
from functools import lru_cache
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple, TypeVar

import requests
from requests.sessions import Session
from typing_extensions import TypeAlias

import pyairtable.api.base
import pyairtable.api.table
from pyairtable.api.params import options_to_json_and_params, options_to_params
from pyairtable.utils import chunked

from .retrying import Retry, _RetryingSession

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
    MAX_RECORDS_PER_REQUEST = 10
    MAX_URL_LENGTH = 16000

    def __init__(
        self,
        api_key: str,
        *,
        timeout: Optional[TimeoutTuple] = None,
        retry_strategy: Optional[Retry] = None,
        endpoint_url: str = "https://api.airtable.com",
    ):
        """
        Args:
            api_key: |arg_api_key|

        Keyword Args:
            timeout: |arg_timeout|
            retry_strategy: |arg_retry_strategy|
            endpoint_url: |arg_endpoint_url|
        """
        if not retry_strategy:
            self.session = Session()
        else:
            self.session = _RetryingSession(retry_strategy)

        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.api_key = api_key

    @property
    def api_key(self) -> str:
        """Returns the Airtable API Key"""
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.session.headers.update({"Authorization": "Bearer {}".format(value)})
        self._api_key = value

    def __repr__(self) -> str:
        return "<pyairtable.Api>"

    def build_url(self, *components: str) -> str:
        """
        Returns a URL to the Airtable API endpoint with the given URL components,
        including the API version number.
        """
        return posixpath.join(self.endpoint_url, self.VERSION, *components)

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

        Keyword Args:
            fallback: The method and URL to use if we have to convert a GET to a POST.
            options: Airtable-specific query params to use while fetching records.
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

    def wait(self) -> None:
        """
        Sleep for 1/N seconds, where N is the maximum RPS allowed by the Airtable API.
        """
        time.sleep(self.API_LIMIT)
