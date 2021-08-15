import abc
from functools import lru_cache
import posixpath
from typing import List, Optional, Tuple
import time
from urllib.parse import quote

import requests

from .params import to_params_dict


class ApiAbstract(metaclass=abc.ABCMeta):
    VERSION = "v0"
    API_BASE_URL = "https://api.airtable.com/"
    API_LIMIT = 1.0 / 5  # 5 per second
    API_URL = posixpath.join(API_BASE_URL, VERSION)
    MAX_RECORDS_PER_REQUEST = 10

    session: requests.Session
    tiemout: Optional[Tuple[int, int]]

    def __init__(self, api_key: str, timeout=None):
        session = requests.Session()
        self.session = session
        self.timeout = timeout
        self.api_key = api_key

    @property
    def api_key(self) -> str:
        """Returns the Airtable API Key"""
        return self._api_key

    @api_key.setter
    def api_key(self, value):
        """Returns the Airtable API Key"""
        self._update_api_key(value)
        self._api_key = value

    def _update_api_key(self, api_key: str) -> None:
        self.session.headers.update({"Authorization": "Bearer {}".format(api_key)})

    @lru_cache()
    def get_table_url(self, base_id: str, table_name: str):
        url_safe_table_name = quote(table_name, safe="")
        table_url = posixpath.join(self.API_URL, base_id, url_safe_table_name)
        return table_url

    @lru_cache()
    def _get_record_url(self, base_id: str, table_name: str, record_id):
        """Builds URL with record id"""
        table_url = self.get_table_url(base_id, table_name)
        return posixpath.join(table_url, record_id)

    def _options_to_params(self, **options):
        """
        Process params names or values as needed using filters
        """
        params = {}
        for name, value in options.items():
            params.update(to_params_dict(name, value))
        return params

    def _chunk(self, iterable, chunk_size):
        """Break iterable into chunks"""
        for i in range(0, len(iterable), chunk_size):
            yield iterable[i : i + chunk_size]

    def _build_batch_record_objects(self, records):
        return [{"fields": record} for record in records]

    def _process_response(self, response):
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

    def _request(self, method: str, url: str, params=None, json_data=None):
        response = self.session.request(
            method, url, params=params, json=json_data, timeout=self.timeout
        )
        return self._process_response(response)

    def _get_record(self, base_id: str, table_name: str, record_id: str) -> dict:
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("get", record_url)

    def _iterate(self, base_id: str, table_name: str, **options):
        offset = None
        params = self._options_to_params(**options)
        while True:
            table_url = self.get_table_url(base_id, table_name)
            if offset:
                params.update({"offset": offset})
            data = self._request("get", table_url, params=params)
            records = data.get("records", [])
            time.sleep(self.API_LIMIT)
            yield records
            offset = data.get("offset")
            if not offset:
                break

    def _first(self, base_id: str, table_name: str, **options) -> Optional[dict]:
        for records in self._iterate(
            base_id, table_name, page_size=1, max_records=1, **options
        ):
            for record in records:
                return record
        return None

    def _all(self, base_id: str, table_name: str, **options) -> List[dict]:
        all_records = []

        for records in self._iterate(base_id, table_name, **options):
            all_records.extend(records)
        return all_records

    def _create(self, base_id: str, table_name: str, fields: dict, typecast=False):

        table_url = self.get_table_url(base_id, table_name)
        return self._request(
            "post",
            table_url,
            json_data={"fields": fields, "typecast": typecast},
        )

    def _batch_create(
        self, base_id: str, table_name: str, records: List[dict], typecast=False
    ) -> List[dict]:

        table_url = self.get_table_url(base_id, table_name)
        inserted_records = []
        for chunk in self._chunk(records, self.MAX_RECORDS_PER_REQUEST):
            new_records = self._build_batch_record_objects(chunk)
            response = self._request(
                "post",
                table_url,
                json_data={"records": new_records, "typecast": typecast},
            )
            inserted_records += response["records"]
            time.sleep(self.API_LIMIT)
        return inserted_records

    def _update(
        self,
        base_id: str,
        table_name: str,
        record_id: str,
        fields: dict,
        replace=False,
        typecast=False,
    ) -> List[dict]:
        record_url = self._get_record_url(base_id, table_name, record_id)

        method = "put" if replace else "patch"
        return self._request(
            method, record_url, json_data={"fields": fields, "typecast": typecast}
        )

    def _batch_update(
        self,
        base_id: str,
        table_name: str,
        records: List[dict],
        replace=False,
        typecast=False,
    ):
        updated_records = []
        table_url = self.get_table_url(base_id, table_name)
        method = "put" if replace else "patch"
        for records in self._chunk(records, self.MAX_RECORDS_PER_REQUEST):
            chunk_records = [{"id": x["id"], "fields": x["fields"]} for x in records]
            response = self._request(
                method,
                table_url,
                json_data={"records": chunk_records, "typecast": typecast},
            )
            updated_records += response["records"]

        return updated_records

    def _delete(self, base_id: str, table_name: str, record_id: str):
        record_url = self._get_record_url(base_id, table_name, record_id)
        return self._request("delete", record_url)

    def _batch_delete(
        self, base_id: str, table_name: str, record_ids: List[str]
    ) -> List[dict]:
        deleted_records = []
        table_url = self.get_table_url(base_id, table_name)
        for record_ids in self._chunk(record_ids, self.MAX_RECORDS_PER_REQUEST):
            delete_results = self._request(
                "delete", table_url, params={"records[]": record_ids}
            )
            deleted_records.extend(delete_results["records"])
            time.sleep(self.API_LIMIT)
        return deleted_records


from pyairtable.api.table import Table  # noqa
from pyairtable.api.base import Base  # noqa
