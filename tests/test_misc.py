import pytest
import requests
from requests_mock import Mocker
import posixpath
from six.moves.urllib.parse import urlencode, quote

from airtable import Airtable
from .pytest_fixtures import mock_airtable, table_url, table_name

class TestAbout():

    def test_get_about_info(self):
        from airtable.__version__ import (__version__,
                                          __name__,
                                          __description__,
                                          __url__,
                                          __author__,
                                          __license__,
                                          __copyright__,
                                          )
        assert __version__
