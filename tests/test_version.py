import pytest

from airtable import Airtable


class TestAbout:
    def test_get_about_info(self):
        from airtable.__version__ import (
            __version__,
            __name__,
            __description__,
            __url__,
            __author__,
            __license__,
            __copyright__,
        )

        assert __version__
