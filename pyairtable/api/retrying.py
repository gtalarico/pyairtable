from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEFAULT_RETRIABLE_STATUS_CODES = (429, 500, 502, 503, 504)
DEFAULT_BACKOFF_FACTOR = 0.3
DEFAULT_MAX_RETRIES = 5


def retry_strategy(
    *,
    status_forcelist=DEFAULT_RETRIABLE_STATUS_CODES,
    backoff_factor=DEFAULT_BACKOFF_FACTOR,
    total=DEFAULT_MAX_RETRIES,
    **kwargs,
) -> Retry:
    """
    Creates a ``Retry`` instance with optional default values.
    See `urllib3 Retry docs <https://urllib3.readthedocs.io/en/stable/reference/urllib3.util.html>`_
    for more details.

    .. versionadded:: 1.4.0

    Keyword Args:
        status_forcelist (``Tuple[int]``): list status code which should be retried.
        backoff_factor (``float``): backoff factor.
        total (``int``): max. number of retries. Note ``0`` means no retries,
            while``1`` will exececute a total of two requests (1 + 1 retry).
        **kwargs: All parameters supported by ``urllib3.util.Retry`` can be used.
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
