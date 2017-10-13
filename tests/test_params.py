from __future__ import absolute_import

import pytest
import os
import requests
from six.moves.urllib.parse import quote

from airtable import Airtable
from airtable.auth import AirtableAuth

from .pytest_fixtures import mock_airtable, table_url

class TestParamsProcess():
    # Ensure kwargs received build a proper params
    # https://codepen.io/airtable/full/rLKkYB

    def test_view_param(self, mock_airtable):
        params = {'view': 'SomeView'}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        target_url_params = "?view=SomeView"
        assert request.prepare().url.endswith(target_url_params)

    def test_max_records_param(self, mock_airtable):
        params = {'max_records': 5}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        target_url_params = "?maxRecords=5"
        assert request.prepare().url.endswith(target_url_params)

    def test_max_records_param_alias(self, mock_airtable):
        params = {'maxRecords': 5}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        target_url_params = "?maxRecords=5"
        assert request.prepare().url.endswith(target_url_params)

    def test_page_size_param(self, mock_airtable):
        params = {'page_size': 5}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        target_url_params = "?pageSize=5"
        assert request.prepare().url.endswith(target_url_params)

    def test_page_size_param_alias(self, mock_airtable):
        params = {'pageSize': 5}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        target_url_params = "?pageSize=5"
        assert request.prepare().url.endswith(target_url_params)

    def test_formula_param(self, mock_airtable):
        params = {'formula': 'NOT(1)'}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?filterByFormula=NOT(1)"
        target_url_params = "?filterByFormula=NOT%281%29"
        assert request.prepare().url.endswith(target_url_params)

    def test_formula_param_alias(self, mock_airtable):
        params = {'filterByFormula': 'NOT(1)'}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?filterByFormula=NOT(1)"
        target_url_params = "?filterByFormula=NOT%281%29"
        assert request.prepare().url.endswith(target_url_params)

    def test_formula_param_quote(self, mock_airtable):
        params = {'formula': 'AND({COLUMN_ID}<=6, {COLUMN_ID}>3)'}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        target_url_params = '?filterByFormula=AND%28%7BCOLUMN_ID%7D%3C%3D6%2C+%7BCOLUMN_ID%7D%3E3%29'
        assert request.prepare().url.endswith(target_url_params)

    def test_fields_param_str(self, mock_airtable):
        params = {'fields': 'Name'}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?fields[]=Name"
        target_url_params = "?fields%5B%5D=Name"
        assert request.prepare().url.endswith(target_url_params)

    def test_fields_param_list(self, mock_airtable):
        params = {'fields': ['Name']}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?fields[]=Name"
        target_url_params = "?fields%5B%5D=Name"
        assert request.prepare().url.endswith(target_url_params)

    def test_fields_param_list_multiple(self, mock_airtable):
        params = {'fields': ['Name', 'Phone']}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?fields[]=Name&fields[]=Phone"
        target_url_params = "?fields%5B%5D=Name&fields%5B%5D=Phone"
        assert request.prepare().url.endswith(target_url_params)

    def test_sort_param_str(self, mock_airtable):
        params = {'sort': 'Name'}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?sort[0][field]=Name&sort[0][direction]=asc"
        target_url_params = '?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name'
        assert request.prepare().url.endswith(target_url_params)

    def test_sort_param_list(self, mock_airtable):
        params = {'sort': ['Name']}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?sort[0][field]=Name&sort[0][direction]=asc"
        target_url_params = "?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name"
        assert request.prepare().url.endswith(target_url_params)

    def test_sort_param_multiple_asc(self, mock_airtable):
        params = {'sort': ['Name', 'Phone']}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = '?sort[0][direction]=asc&sort[0][field]=Name&sort[1][direction]=asc&sort[1][field]=Phone'
        target_url_params = '?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=asc&sort%5B1%5D%5Bfield%5D=Phone'
        assert request.prepare().url.endswith(target_url_params)

    def test_sort_param_multiple_mixed(self, mock_airtable):
        params = {'sort': ['Name', '-Phone']}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = '?sort[0][direction]=desc&sort[0][field]=Name&sort[1][direction]=desc&sort[1][field]=Phone'
        target_url_params = '?sort%5B0%5D%5Bdirection%5D=asc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=desc&sort%5B1%5D%5Bfield%5D=Phone'
        assert request.prepare().url.endswith(target_url_params)

    def test_sort_param_multiple_explicit(self, mock_airtable):
        params = {'sort': [('Name', 'desc'), ('Phone', 'asc')]}
        processed_params = mock_airtable._process_params(params)
        request = requests.Request('get', table_url, params=processed_params)
        # target_url_params = "?sort[0][direction]=desc&sort[0][field]=Name&sort[1][direction]=asc&sort[1][field]=Phone"
        target_url_params = '?sort%5B0%5D%5Bdirection%5D=desc&sort%5B0%5D%5Bfield%5D=Name&sort%5B1%5D%5Bdirection%5D=asc&sort%5B1%5D%5Bfield%5D=Phone'
        assert request.prepare().url.endswith(target_url_params)
