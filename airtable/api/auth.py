import requests


class AirtableAuth(requests.auth.AuthBase):
    def __init__(self, api_key):
        """
        Authentication used by Airtable Class

        Args:
            api_key (``str``): Airtable API Key.
        """
        self.api_key = api_key

    def __call__(self, request):
        auth_token = {"Authorization": "Bearer {}".format(self.api_key)}
        request.headers.update(auth_token)
        return request
