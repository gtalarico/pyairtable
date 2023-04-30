import pytest
import requests
from requests_mock import Mocker

from pyairtable.api.params import (
    InvalidParamException,
    dict_list_to_request_params,
    field_names_to_sorting_dict,
    options_to_json_and_params,
    options_to_params,
    to_params_dict,
)


def test_params_integration(table, mock_records, mock_response_iterator):
    params = {
        "max_records": 1,
        "view": "View",
        "sort": ["Name"],
        "fields": ["Name", "Age"],
        "return_fields_by_field_id": True,
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
def test_convert_options_to_params(option, value, url_params):
    """Ensure kwargs received build a proper params"""
    processed_params = options_to_params({option: value})
    request = requests.Request("get", "https://example.com", params=processed_params)
    assert request.prepare().url.endswith(url_params)

    # TODO: remove in 2.0.0
    with pytest.deprecated_call():
        processed_params = to_params_dict(option, value)

    request = requests.Request("get", "https://example.com", params=processed_params)
    assert request.prepare().url.endswith(url_params)


@pytest.mark.parametrize(
    "option,value,expected",
    [
        ["view", "SomeView", {"view": "SomeView"}],
        ["max_records", 5, {"maxRecords": 5}],
        ["page_size", 5, {"pageSize": 5}],
        ["formula", "NOT(1)", {"filterByFormula": "NOT(1)"}],
        ["formula", "NOT(1)", {"filterByFormula": "NOT(1)"}],
        [
            "formula",
            "AND({COLUMN_ID}<=6, {COLUMN_ID}>3)",
            {"filterByFormula": "AND({COLUMN_ID}<=6, {COLUMN_ID}>3)"},
        ],
        ["fields", ["Name"], {"fields": ["Name"]}],
        [
            "fields",
            ["Name", "Phone"],
            {"fields": ["Name", "Phone"]},
        ],
        [
            "sort",
            ["Name"],
            {"sort": [{"field": "Name", "direction": "asc"}]},
        ],
        [
            "sort",
            ["Name", "Phone"],
            {
                "sort": [
                    {"field": "Name", "direction": "asc"},
                    {"field": "Phone", "direction": "asc"},
                ]
            },
        ],
        [
            "sort",
            ["Name", "-Phone"],
            {
                "sort": [
                    {"field": "Name", "direction": "asc"},
                    {"field": "Phone", "direction": "desc"},
                ]
            },
        ],
        ["cell_format", "string", {"cellFormat": "string"}],
        ["return_fields_by_field_id", True, {"returnFieldsByFieldId": True}],
        ["return_fields_by_field_id", 1, {"returnFieldsByFieldId": True}],
        ["return_fields_by_field_id", False, {"returnFieldsByFieldId": False}],
        # userLocale and timeZone are not supported via POST, so they return "spare params"
        ["user_locale", "en-US", ({}, {"userLocale": "en-US"})],
        ["time_zone", "America/Chicago", ({}, {"timeZone": "America/Chicago"})],
    ],
)
def test_convert_options_to_json(option, value, expected):
    if isinstance(expected, dict):
        expected = (expected, {})  # most of the time, this returns empty "spare params"
    assert options_to_json_and_params({option: value}) == expected


def test_process_params_invalid():
    with pytest.raises(InvalidParamException):
        options_to_params({"ffields": "x"})


def test_dict_list_to_request_params():
    values = [{"field": "a", "direction": "asc"}, {"field": "b", "direction": "desc"}]
    rv = dict_list_to_request_params("sort", values)
    assert rv == {
        "sort[0][field]": "a",
        "sort[0][direction]": "asc",
        "sort[1][field]": "b",
        "sort[1][direction]": "desc",
    }


def test_field_names_to_sorting_dict():
    rv = field_names_to_sorting_dict(["Name", "-Age"])
    assert rv == [
        {
            "field": "Name",
            "direction": "asc",
        },
        {
            "field": "Age",
            "direction": "desc",
        },
    ]
