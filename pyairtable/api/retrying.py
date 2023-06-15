from typing import Any, Tuple, Union

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_RETRIABLE_STATUS_CODES = (429, 500, 502, 503, 504)
DEFAULT_BACKOFF_FACTOR = 0.3
DEFAULT_MAX_RETRIES = 5


def retry_strategy(
    *,
    status_forcelist: Tuple[int, ...] = DEFAULT_RETRIABLE_STATUS_CODES,
    backoff_factor: Union[int, float] = DEFAULT_BACKOFF_FACTOR,
    total: int = DEFAULT_MAX_RETRIES,
    **kwargs: Any,
) -> Retry:
    """
    Creates a ``Retry`` instance with optional default values.
    See `urllib3.util.Retry`_ for more details.

    .. versionadded:: 1.4.0

    Args:
        status_forcelist: Status codes which should be retried.
        backoff_factor:
            A backoff factor to apply between attempts after the second try.
            Sleep time between each request will be calculated as
            ``backoff_factor * (2 ** (retry_count - 1))``
        total:
            Maximum number of retries. Note that ``0`` means no retries,
            whereas ``1`` will execute a total of two requests (original + 1 retry).
        **kwargs: Any valid parameter to `urllib3.util.Retry <https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html#urllib3.util.Retry>`_.
    """
    return Retry(
        total=total,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        **kwargs,
    )


class _RetryingSession(Session):
    def __init__(self, retry_strategy: Retry):
        super().__init__()

        adapter = HTTPAdapter(max_retries=retry_strategy)

        self.mount("https://", adapter)
        self.mount("http://", adapter)


__all__ = [
    "Retry",
    "_RetryingSession",
]
