import abc
import posixpath
import time
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, Iterator, List, Optional, Tuple
from urllib.parse import quote

import requests
from requests.sessions import Session
from typing_extensions import TypeAlias

from pyairtable.api.types import (
    FieldName,
    Fields,
    RecordDeletedDict,
    RecordDict,
    RecordId,
    UpdateRecordDict,
    assert_typed_dict,
    assert_typed_dicts,
)
from pyairtable.utils import chunked

from .params import options_to_json_and_params, options_to_params
from .retrying import Retry, _RetryingSession

TimeoutTuple: TypeAlias = Tuple[int, int]


if TYPE_CHECKING:
    from pyairtable.api.base import Base  # noqa
    from pyairtable.api.table import Table  # noqa


class ApiAbstract(metaclass=abc.ABCMeta):
    VERSION = "v0"
    API_LIMIT = 1.0 / 5  # 5 per second
    MAX_RECORDS_PER_REQUEST = 10
    MAX_URL_LENGTH = 16000

    session: Session
    endpoint_url: str
    timeout: Optional[TimeoutTuple]

    def __init__(
        self,
        api_key: str,
        timeout: Optional[TimeoutTuple] = None,
        retry_strategy: Optional[Retry] = None,
        endpoint_url: str = "https://api.airtable.com",
    ):
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
        """Returns the Airtable API Key"""
        self._update_api_key(value)
        self._api_key = value

    def build_url(self, *components: str) -> str:
        """
        Returns a URL to the Airtable API endpoint with the given URL components,
        including the API version number.
        """
        return posixpath.join(self.endpoint_url, self.VERSION, *components)

    def _update_api_key(self, api_key: str) -> None:
        self.session.headers.update({"Authorization": "Bearer {}".format(api_key)})

    @lru_cache()
    def get_table_url(self, base_id: str, table_name: str) -> str:
        url_safe_table_name = quote(table_name, safe="")
        return self.build_url(base_id, url_safe_table_name)

    @lru_cache()
    def _get_record_url(
        self, base_id: str, table_name: str, record_id: RecordId
    ) -> str:
        """Builds URL with record id"""
        table_url = self.get_table_url(base_id, table_name)
        return posixpath.join(table_url, record_id)

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

    def _request(
        self,
        method: str,
        url: str,
        fallback_post_url: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[Any, Any]] = None,
    ) -> Any:
        """
        Makes a request to the Airtable API, optionally converting a GET to a POST
        if the URL exceeds the API's maximum URL length.

        See https://support.airtable.com/docs/enforcement-of-url-length-limit-for-web-api-requests

        Args:
            method (``str``): HTTP method to use.
            url (``str``): The URL we're attempting to call.

        Keyword Args:
            fallback_post_url (``str``, optional): The URL to use if we have to convert a GET to a POST.
            options (``dict``, optional): Airtable-specific query params to use while fetching records.
            params (``dict``, optional): Additional query params to append to the URL as-is.
            json_data (``dict``, optional): The JSON payload for a POST/PUT/PATCH/DELETE request.
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
                json=json_data,
            )
        )

        # If our URL is too long, move *most* (not all) query params into a POST body.
        if (
            len(str(prepared.url)) >= self.MAX_URL_LENGTH
            and method.upper() == "GET"
            and fallback_post_url
        ):
            json_data, spare_params = options_to_json_and_params(options or {})
            return self._request(
                method="POST",
                url=fallback_post_url,
                params={**spare_params, **(params or {})},
                json_data=json_data,
            )

        response = self.session.send(prepared, timeout=self.timeout)
        return self._process_response(response)

    def _get_record(
        self,
        base_id: str,
        table_name: str,
        record_id: RecordId,
        **options: Any,
    ) -> RecordDict:
        record_url = self._get_record_url(base_id, table_name, record_id)
        return assert_typed_dict(
            RecordDict, self._request("get", record_url, options=options)
        )

    def _iterate(
        self, base_id: str, table_name: str, **options: Any
    ) -> Iterator[List[RecordDict]]:
        offset = None
        table_url = self.get_table_url(base_id, table_name)
        while True:
            if offset:
                options.update({"offset": offset})
            data = self._request(
                method="get",
                url=table_url,
                fallback_post_url=f"{table_url}/listRecords",
                options=options,
            )
            records = assert_typed_dicts(RecordDict, data.get("records", []))
            yield records
            offset = data.get("offset")
            if not offset:
                break
            time.sleep(self.API_LIMIT)

    def _first(
        self, base_id: str, table_name: str, **options: Any
    ) -> Optional[RecordDict]:
        for records in self._iterate(
            base_id, table_name, page_size=1, max_records=1, **options
        ):
            for record in records:
                return record
        return None

    def _all(self, base_id: str, table_name: str, **options: Any) -> List[RecordDict]:
        all_records = []
        for records in self._iterate(base_id, table_name, **options):
            all_records.extend(records)
        return all_records

    def _create(
        self,
        base_id: str,
        table_name: str,
        fields: Fields,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> RecordDict:
        table_url = self.get_table_url(base_id, table_name)
        created = self._request(
            "post",
            table_url,
            json_data={
                "fields": fields,
                "typecast": typecast,
                "returnFieldsByFieldId": return_fields_by_field_id,
            },
        )
        return assert_typed_dict(RecordDict, created)

    def _batch_create(
        self,
        base_id: str,
        table_name: str,
        records: List[Fields],
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> List[RecordDict]:
        table_url = self.get_table_url(base_id, table_name)
        inserted_records = []
        for chunk in chunked(records, self.MAX_RECORDS_PER_REQUEST):
            new_records = [{"fields": fields} for fields in chunk]
            response = self._request(
                "post",
                table_url,
                json_data={
                    "records": new_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": return_fields_by_field_id,
                },
            )
            inserted_records += assert_typed_dicts(RecordDict, response["records"])
            time.sleep(self.API_LIMIT)
        return inserted_records

    def _update(
        self,
        base_id: str,
        table_name: str,
        record_id: RecordId,
        fields: Fields,
        replace: bool = False,
        typecast: bool = False,
    ) -> RecordDict:
        record_url = self._get_record_url(base_id, table_name, record_id)
        method = "put" if replace else "patch"
        updated = self._request(
            method,
            record_url,
            json_data={"fields": fields, "typecast": typecast},
        )
        return assert_typed_dict(RecordDict, updated)

    def _batch_update(
        self,
        base_id: str,
        table_name: str,
        records: List[UpdateRecordDict],
        replace: bool = False,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> List[RecordDict]:
        updated_records = []
        table_url = self.get_table_url(base_id, table_name)
        method = "put" if replace else "patch"
        for chunk in chunked(records, self.MAX_RECORDS_PER_REQUEST):
            chunk_records = [{"id": x["id"], "fields": x["fields"]} for x in chunk]
            response = self._request(
                method,
                table_url,
                json_data={
                    "records": chunk_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": return_fields_by_field_id,
                },
            )
            updated_records += assert_typed_dicts(RecordDict, response["records"])
            time.sleep(self.API_LIMIT)

        return updated_records

    def _batch_upsert(
        self,
        base_id: str,
        table_name: str,
        records: List[UpdateRecordDict],
        key_fields: List[FieldName],
        replace: bool = False,
        typecast: bool = False,
        return_fields_by_field_id: bool = False,
    ) -> List[RecordDict]:
        # The API will reject a request where a record is missing any of fieldsToMergeOn,
        # but we might not reach that error until we've done several batch operations.
        # To spare implementers from having to recover from a partially applied upsert,
        # and to simplify our API, we will raise an exception before any network calls.
        for record in records:
            if "id" in record:
                continue
            missing = set(key_fields) - set(record.get("fields", []))
            if missing:
                raise ValueError(f"missing {missing!r} in {record['fields'].keys()!r}")

        updated_records = []
        table_url = self.get_table_url(base_id, table_name)
        method = "put" if replace else "patch"
        for chunk in chunked(records, self.MAX_RECORDS_PER_REQUEST):
            formatted_records = [
                {k: v for (k, v) in record.items() if k in ("id", "fields")}
                for record in chunk
            ]
            response = self._request(
                method,
                table_url,
                json_data={
                    "records": formatted_records,
                    "typecast": typecast,
                    "returnFieldsByFieldId": return_fields_by_field_id,
                    "performUpsert": {"fieldsToMergeOn": key_fields},
                },
            )
            updated_records += assert_typed_dicts(RecordDict, response["records"])
            time.sleep(self.API_LIMIT)

        return updated_records

    def _delete(
        self, base_id: str, table_name: str, record_id: RecordId
    ) -> RecordDeletedDict:
        record_url = self._get_record_url(base_id, table_name, record_id)
        return assert_typed_dict(RecordDeletedDict, self._request("delete", record_url))

    def _batch_delete(
        self, base_id: str, table_name: str, record_ids: List[RecordId]
    ) -> List[RecordDeletedDict]:
        deleted_records = []
        table_url = self.get_table_url(base_id, table_name)
        for chunk in chunked(record_ids, self.MAX_RECORDS_PER_REQUEST):
            delete_results = self._request(
                "delete", table_url, params={"records[]": chunk}
            )
            deleted_records += assert_typed_dicts(
                RecordDeletedDict, delete_results["records"]
            )
            time.sleep(self.API_LIMIT)
        return deleted_records
