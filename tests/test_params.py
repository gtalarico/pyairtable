import pytest
import requests
from posixpath import join as urljoin
from requests_mock import Mocker

from pyairtable.api.params import (
    to_params_dict,
    dict_list_to_request_params,
    field_names_to_sorting_dict,
    InvalidParamException,
)


def test_params_integration_all_query(table, mock_records, mock_response_single):
    params = {
        "max_records": 1,
        "view": "View",
        "sort": ["Name"],
        "fields": ["Name", "Age"],
        "return_fields_by_field_id": True,
        "time_zone": "utc",
        "user_locale": "es",
    }
    with Mocker() as m:
        url_params = (
            "maxRecords=1"
            "&sort%5B0%5D%5Bdirection%5D=asc"
            "&sort%5B0%5D%5Bfield%5D=Name"
            "&view=View"
            "&fields%5B%5D=Name"
            "&fields%5B%5D=Age"
            "&returnFieldsByFieldId=1"
            "&timeZone=utc"
            "&userLocale=es"
        )
        mock_url = "{0}?{1}".format(table.get_record_url("rec"), url_params)
        m.get(mock_url, status_code=200, json=mock_response_single)
        response = table.get("rec", **params)
    assert response["id"] == mock_response_single["id"]


def test_params_integration_list_records_post(
    table, mock_records, mock_response_iterator, json_matcher
):
    options = {
        "view": "View",
        "sort": ["Name"],
        "fields": ["Name", "Age"],
        "return_fields_by_field_id": True,
        "time_zone": "utc",
        "user_locale": "es",
    }
    with Mocker() as m:
        json_data = {
            "view": "View",
            "sort": [{"field": "Name", "direction": "asc"}],
            "fields": ["Name", "Age"],
            "returnFieldsByFieldId": True,
            # This are added only because of our use of first() in tes
            "maxRecords": 1,
            "pageSize": 1,
        }
        url_params = "timeZone=utc&userLocale=es"

        mock_url = "{0}?{1}".format(urljoin(table.table_url, "listRecords"), url_params)
        m.post(
            mock_url,
            additional_matcher=json_matcher(json_data),
            status_code=200,
            json=mock_response_iterator,
        )
        response = table.first(**options)
        assert response["id"] == mock_records[0]["id"]


@pytest.mark.parametrize(
    "option,value,url_params",
    [
        ["view", "SomeView", "?view=SomeView"],
        ["max_records", 5, "?maxRecords=5"],
        ["page_size", 5, "?pageSize=5"],
        ["formula", "NOT(1)", "?filterByFormula=NOT%281%29"],
        ["formula", "NOT(1)", "?filterByFormula=NOT%281%29"],
        [
            "formula",
            r"AND({COLUMN_ID}<=6, {COLUMN_ID}>3)",
            "?filterByFormula=AND%28%7BCOLUMN_ID%7D%3C%3D6%2C+%7BCOLUMN_ID%7D%3E3%29",
        ],
        [
            "fields",
            ["Name"],
            "?fields%5B%5D=Name",
            # ?fields[]=Name",
        ],
        [
            "fields",
            ["Name"],
            "?fields%5B%5D=Name",
            # "?fields[]=Name",
        ],
        [
            "fields",
            ["Name", "Phone"],
            "?fields%5B%5D=Name&fields%5B%5D=Phone",
            # "?fields[]=Name&fields[]=Phone",
        ],
        [
            "sort",
            ["Name"],
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name",
            # "?sort[0][field]=Name&sort[0][direction]=asc",
        ],
        [
            "sort",
            ["Name"],
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name",
            # "?sort[0][field]=Name&sort[0][direction]=asc"
        ],
        [
            "sort",
            ["Name", "Phone"],
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=asc&sort%5B1%5D%5Bfield%5D=Phone",
            # '?sort[0][direction]=asc&sort[0][field]=Name&sort[1][direction]=asc&sort[1][field]=Phone'
        ],
        [
            "sort",
            ["Name", "-Phone"],
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=desc&sort%5B1%5D%5Bfield%5D=Phone",
            # '?sort[0][direction]=desc&sort[0][field]=Name&sort[1][direction]=desc&sort[1][field]=Phone'
        ],
        ["cell_format", "string", "?cellFormat=string"],
        ["user_locale", "en-US", "?userLocale=en-US"],
        [
            "time_zone",
            "America/Chicago",
            "?timeZone=America%2FChicago"
            # '?timeZone=America/Chicago'
        ],
        ["return_fields_by_field_id", True, "?returnFieldsByFieldId=1"],
        ["return_fields_by_field_id", 1, "?returnFieldsByFieldId=1"],
        ["return_fields_by_field_id", False, "?returnFieldsByFieldId=0"],
        # TODO
        # [
        #     {"sort": [("Name", "desc"), ("Phone", "asc")]},
        #     # "?sort[0][direction]=desc&sort[0][field]=Name&sort[1][direction]=asc&sort[1][field]=Phone"
        #     "?sort%5B0%5D%5Bdirection%5D=desc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=asc&sort%5B1%5D%5Bfield%5D=Phone",
        # ],
    ],
)
def test_process_params(option, value, url_params):
    """Ensure kwargs received build a proper params"""
    # https://codepen.io/airtable/full/rLKkYB

    processed_params = to_params_dict(option, value)
    request = requests.Request("get", "https://fake.com", params=processed_params)
    assert request.prepare().url.endswith(url_params)


def test_process_params_invalid():
    with pytest.raises(InvalidParamException):
        to_params_dict("ffields", "x")


def test_dict_list_to_request_params():
    values = [{"field": "a", "direction": "asc"}, {"field": "b", "direction": "desc"}]
    rv = dict_list_to_request_params("sort", values)
    assert rv["sort[0][field]"] == "a"
    assert rv["sort[0][direction]"] == "asc"
    assert rv["sort[1][field]"] == "b"
    assert rv["sort[1][direction]"] == "desc"


def test_field_names_to_sorting_dict():
    rv = field_names_to_sorting_dict(["Name", "-Age"])
    assert rv[0]["field"] == "Name"
    assert rv[0]["direction"] == "asc"
    assert rv[1]["field"] == "Age"
    assert rv[1]["direction"] == "desc"
