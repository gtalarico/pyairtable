import pytest
import requests
from requests_mock import Mocker

from pyairtable.api.params import (
    to_params_dict,
    dict_list_to_request_params,
    field_names_to_sorting_dict,
    InvalidParamException,
)


def test_params_integration(table, mock_records, mock_response_iterator):
    params = {
        "max_records": 1,
        "view": "View",
        "sort": ["Name"],
        "fields": ["Name", "Age"],
    }
    with Mocker() as m:
        url_params = (
            "maxRecords=1"
            "&sort%5B0%5D%5Bdirection%5D=asc"
            "&sort%5B0%5D%5Bfield%5D=Name"
            "&view=View"
            "&fields%5B%5D=Name"
            "&fields%5B%5D=Age"
            ""
        )
        mock_url = "{0}?{1}".format(table.table_url, url_params)
        m.get(mock_url, status_code=200, json=mock_response_iterator)
        response = table.all(**params)
    for n, resp in enumerate(response):
        resp["id"] == mock_records[n]["id"]


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
