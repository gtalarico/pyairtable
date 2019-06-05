from __future__ import absolute_import

import pytest
import os
import requests
from requests_mock import Mocker
from six.moves.urllib.parse import quote

from airtable import Airtable
from airtable.params import AirtableParams
from airtable.auth import AirtableAuth


class TestParamsIntegration:
    def test_params_integration(self, table, mock_records, mock_response_iterator):
        params = {"max_records": 1, "view": "View", "sort": "Name"}
        with Mocker() as m:
            mock_url = "{}?maxRecords=1&sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name&view=View".format(
                table.url_table
            )
            m.get(mock_url, status_code=200, json=mock_response_iterator)
            response = table.get_all(**params)
        for n, resp in enumerate(response):
            resp["id"] == mock_records[n]["id"]


@pytest.mark.parametrize(
    "kwargs,url_params",
    [
        [{"view": "SomeView"}, "?view=SomeView"],
        [{"max_records": 5}, "?maxRecords=5"],
        [{"maxRecords": 3}, "?maxRecords=3"],
        [{"page_size": 5}, "?pageSize=5"],
        [{"pageSize": 2}, "?pageSize=2"],
        [
            {"formula": "NOT(1)"},
            # ?filterByFormula=NOT(1)"
            "?filterByFormula=NOT%281%29",
        ],
        [{"filterByFormula": "NOT(1)"}, "?filterByFormula=NOT%281%29"],
        [
            {"formula": r"AND({COLUMN_ID}<=6, {COLUMN_ID}>3)"},
            "?filterByFormula=AND%28%7BCOLUMN_ID%7D%3C%3D6%2C+%7BCOLUMN_ID%7D%3E3%29",
        ],
        [
            {"fields": "Name"},
            # ?fields[]=Name",
            "?fields%5B%5D=Name",
        ],
        [
            {"fields": ["Name"]},
            # "?fields[]=Name",
            "?fields%5B%5D=Name",
        ],
        [
            {"fields": ["Name", "Phone"]},
            # "?fields[]=Name&fields[]=Phone",
            "?fields%5B%5D=Name&fields%5B%5D=Phone",
        ],
        [
            {"sort": "Name"},
            # "?sort[0][field]=Name&sort[0][direction]=asc",
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name",
        ],
        [
            {"sort": ["Name"]},
            # "?sort[0][field]=Name&sort[0][direction]=asc"
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name",
        ],
        [
            {"sort": ["Name", "Phone"]},
            # '?sort[0][direction]=asc&sort[0][field]=Name&sort[1][direction]=asc&sort[1][field]=Phone'
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=asc&sort%5B1%5D%5Bfield%5D=Phone",
        ],
        [
            {"sort": ["Name", "-Phone"]},
            # '?sort[0][direction]=desc&sort[0][field]=Name&sort[1][direction]=desc&sort[1][field]=Phone'
            "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=desc&sort%5B1%5D%5Bfield%5D=Phone",
        ],
        [
            {"sort": [("Name", "desc"), ("Phone", "asc")]},
            # "?sort[0][direction]=desc&sort[0][field]=Name&sort[1][direction]=asc&sort[1][field]=Phone"
            "?sort%5B0%5D%5Bdirection%5D=desc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=asc&sort%5B1%5D%5Bfield%5D=Phone",
        ],
    ],
)
def test_process_params(kwargs, url_params):
    """ Ensure kwargs received build a proper params """
    # https://codepen.io/airtable/full/rLKkYB

    FAKE_URL = "http://www.fake.com"
    table = Airtable("x", "y", api_key="z")
    processed_params = table._process_params(kwargs)
    request = requests.Request("get", FAKE_URL, params=processed_params)
    assert request.prepare().url.endswith(url_params)


def test_formula_from_name_and_value():
    formula = AirtableParams.FormulaParam.from_name_and_value("COL", "VAL")
    assert formula == r"{COL}='VAL'"

    formula = AirtableParams.FormulaParam.from_name_and_value("COL", 8)
    assert formula == r"{COL}=8"
