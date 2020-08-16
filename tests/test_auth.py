import requests
from requests_mock import Mocker
from airtable.auth import AirtableAuth


class TestAuth(object):
    def test_authorization_key(self, table):
        FAKE_URL = "http://www.fake.com"
        session = requests.Session()
        session.auth = AirtableAuth(api_key="xxx")
        with Mocker() as m:
            m.get(FAKE_URL)
            resp = session.get(FAKE_URL)
        assert "Authorization" in resp.request.headers
        assert "Bearer xxx" in resp.request.headers["Authorization"]

    def test_authorization_manual_call(self):
        request = requests.Request()
        auth = AirtableAuth(api_key="x")
        request = auth.__call__(request)
        assert "Authorization" in request.headers
        assert "Bearer" in request.headers["Authorization"]
