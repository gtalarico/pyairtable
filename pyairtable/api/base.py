import warnings
from functools import lru_cache
from typing import Union

import pyairtable.api.api
import pyairtable.api.table


class Base:
    """
    Represents an Airtable base.
    """

    api: "pyairtable.api.api.Api"
    id: str

    def __init__(self, api: Union["pyairtable.api.api.Api", str], base_id: str):
        """
        Old style constructor takes ``str`` arguments, and will create its own
        instance of :class:`Api`.

        This approach is deprecated, and will likely be removed in the future.

            >>> Base("access_token", "base_id")

        New style constructor takes an instance of :class:`Api`:

            >>> Base(api, "table_name")

        Args:
            api: An instance of :class:`Api` or an Airtable access token.
            base_id: |arg_base_id|
        """
        if isinstance(api, str):
            warnings.warn(
                "Passing API keys to pyairtable.Base is deprecated; use Api.base() instead."
                " See https://pyairtable.rtfd.org/en/latest/migrations.html for details.",
                category=DeprecationWarning,
                stacklevel=2,
            )
            api = pyairtable.api.api.Api(api)

        self.api = api
        self.id = base_id

    def __repr__(self) -> str:
        return f"<pyairtable.Base base_id={self.id!r}>"

    @lru_cache
    def table(self, table_name: str) -> "pyairtable.api.table.Table":
        """
        Returns a new :class:`Table` instance using all shared
        attributes from :class:`Base`.

        Args:
            table_name: An Airtable table name. Table name should be unencoded,
                as shown on browser.
        """
        return pyairtable.api.table.Table(None, self, table_name)

    @property
    def url(self) -> str:
        return self.api.build_url(self.id)
