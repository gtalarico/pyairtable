# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import requests


def _versiontuple(v):
    return tuple(map(int, (v.split("."))))


_requests_version = _versiontuple(requests.__version__)


class _FakeHTTPMessage(object):

    def __init__(self, headers):
        self.headers = headers

    def getheaders(self, name):
        try:
            return [self.headers[name]]
        except KeyError:
            return []

    def get_all(self, name, failobj=None):
        # python 3 only, overrides email.message.Message.get_all
        try:
            return [self.headers[name]]
        except KeyError:
            return failobj


class _FakeHTTPResponse(object):

    def __init__(self, headers):
        self.msg = _FakeHTTPMessage(headers)

    def isclosed(self):
        # Don't let urllib try to close me
        return False


if _requests_version < (2, 3):
    # NOTE(jamielennox): There is a problem with requests < 2.3.0 such that it
    # needs a httplib message for use with cookie extraction. It has been fixed
    # but it is needed until we can rely on a recent enough requests version.

    _fake_http_response = _FakeHTTPResponse({})

else:
    _fake_http_response = None
