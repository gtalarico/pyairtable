"""
Authentication is handled by the :any:`Airtable` class.

>>> airtable = Airtable(base_key, table_name, api_key='your_api_key')

Alternatively, you can leave the api_key, and the library will look for
an enviroment variable named ``AIRTABLE_API_KEY``.

>>> airtable = Airtable(base_key, table_name)

Note:
    You can also use this class to handle authentication for you if you are
    making your own wrapper:

    >>> auth = AirtableAuth(api_key)
    >>> response = requests.get('https://api.airtable.com/v0/appZkOEliMniglNQo/table', auth=auth)

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
            raise KeyError('AIRTABLE_API_KEY not found')

    def __call__(self, request):
        request.headers.update({'Authorization': 'Bearer {}'.format(self.api_key)})
        return request
