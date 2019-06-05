import pytest


def match_request_data(post_data):
    """ Custom Matches, check that provided Request data is correct"""
    def _match_request_data(request):
        request_data_fields = request.json()['fields']
        return dict_equals(request_data_fields, post_data)
    return _match_request_data


def dict_equals(d1, d2):
    return sorted(d1.items()) == sorted(d2.items())
