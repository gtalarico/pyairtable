"""
Authentication is handled by the :any:`Airtable` class.
The class can handle authentication automatically
if the environment variable `AIRTABLE_API_KEY` is set with your api key.

>>> airtable = Airtable(base_key, table_name)

Alternatively, you can pass the key explicitly:

>>> airtable = Airtable(base_key, table_name, api_key='yourapikey')

Note:
    You can also use this class to handle authentication for you if you
    are making your own wrapper:

    >>> auth = AirtableAuth(api_key)
    >>> response = requests.get('https://api.airtable.com/v0/{basekey}/{table_name}', auth=auth)

"""  #
from __future__ import absolute_import
import os
import requests


class AirtableAuth(requests.auth.AuthBase):

    def __init__(self, api_key=None):
        """
        Authentication used by Airtable Class

        Args:
            api_key (``str``): Airtable API Key. Optional.
                If not set, it will look for
                enviroment variable ``AIRTABLE_API_KEY``
        """
        try:
            self.api_key = api_key or os.environ['AIRTABLE_API_KEY']
        except KeyError:
            raise KeyError('Api Key not found. Pass api_key as a kwarg \
                            or set an env var AIRTABLE_API_KEY with your key')

    def __call__(self, request):
        request.headers.update({'Authorization': 'Bearer {}'.format(self.api_key)})
        return request
