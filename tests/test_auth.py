from __future__ import absolute_import

import pytest
import os
import requests

from airtable import Airtable
from airtable.auth import AirtableAuth

from .pytest_fixtures import table_name, base_key

class TestAuth():

    def test_authorization_scheme(self):
        session = requests.Session()
        session.auth = AirtableAuth()
        resp = session.get('http://www.google.com')
        assert 'Authorization' in resp.request.headers
        assert 'Bearer' in resp.request.headers['Authorization']

    def test_authorization_manual_call(self):
        session = requests.Session()
        auth = AirtableAuth()
        session = auth.__call__(session)
        assert 'Authorization' in session.headers
        assert 'Bearer' in session.headers['Authorization']

    def test_authorization_missing(self):
        key = os.environ.pop('AIRTABLE_API_KEY')
        session = requests.Session()
        with pytest.raises(KeyError):
            session.auth = AirtableAuth()
        os.environ['AIRTABLE_API_KEY'] = key

    def test_authorization_manual_key(self):
        key = os.environ['AIRTABLE_API_KEY']
        session = requests.Session()
        session.auth = AirtableAuth(api_key=key)
        resp = session.get('http://www.google.com')
        assert 'Authorization' in resp.request.headers
        assert 'Bearer' in resp.request.headers['Authorization']

    def test_authorization_fail(self, ):
        with pytest.raises(ValueError) as excinfo:
            # Raises Invalid Base Key or Table Name
            fake_airtable = Airtable(base_key='XXX', table_name='YYY')
        errmsg = str(excinfo.value).lower()
        assert 'invalid' in errmsg and 'base' in errmsg

    def test_authorization_bad_credentials(self, ):
        with pytest.raises(ValueError) as excinfo:
            # Raises Invalid Table Name
            fake_airtable = Airtable(base_key=base_key,
                                     table_name=table_name,
                                     api_key='BADKEY')
        assert 'authentication failed' in str(excinfo.value).lower()

