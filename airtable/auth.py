""" Airtable Python Wrapper  """
from __future__ import absolute_import
import os
import requests


class AirtableAuth(requests.auth.AuthBase):

    def __init__(self, API_KEY=None):
        """
        Custome Authentication used by Airtable Class
        """
        try:
            self.api_key = API_KEY or os.environ['AIRTABLE_API_KEY']
        except KeyError:
            raise KeyError('AIRTABLE_API_KEY not found')

    def __call__(self, request):
        request.headers.update({'Authorization': 'Bearer {}'.format(self.api_key)})
        return request
