"""
Authentication is handled by the :any:`Airtable` class.

>>> airtable = Airtable(base_id, table_name, api_key)

Note:
    You can also use this class to handle authentication for you if you
    are making your own wrapper:

    >>> auth = AirtableAuth(api_key)
    >>> response = requests.get('https://api.airtable.com/v0/{base_id}/{table_name}', auth=auth)

"""  #
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
