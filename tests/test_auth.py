import os

import pytest
from mock import Mock

from airtable.table import Airtable
from airtable.auth import AirtableAuth
from requests import Session

API_KEY_ENV_NAME = 'AIRTABLE_API_KEY'


class Environ:

    def __enter__(self):
        self.envvar = os.environ.get(API_KEY_ENV_NAME)

    def __exit__(self, *args):
        if self.envvar is not None:
            os.environ[API_KEY_ENV_NAME] = self.envvar


def test_api_key_provided():
    auth = AirtableAuth('API Key')
    assert auth.api_key == 'API Key'

    request = auth(Session())
    assert request.headers['Authorization'] == 'Bearer API Key'


def test_api_key_found_in_environ_var():
    with Environ():
        os.environ[API_KEY_ENV_NAME] = 'ENV API Key'
        auth = AirtableAuth()
        assert auth.api_key == 'ENV API Key'


def test_api_key_not_provided():
    with Environ():
        del os.environ[API_KEY_ENV_NAME]
        with pytest.raises(KeyError):
            AirtableAuth()


def test_airtable_validate_session_option():
    AirtableAuth = Mock(name='AirtableAuth')
    Airtable.validate_session = Mock(
        name='validate_session', return_value=True
    )
    at = Airtable('base_key', 'api_key')
    Airtable.validate_session.called_with(at.url_table)
    Airtable.validate_session.called_once()
