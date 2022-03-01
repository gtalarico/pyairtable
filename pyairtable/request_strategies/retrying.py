from typing import Any, Optional, overload
from requests import Response, Session
from .simple import SimpleRequestStrategy

try:
    from tenacity import Retrying
except ImportError:
    TENACITY_FOUND = False
    Retrying = Any
    retry_base = Any
    wait_base = Any
    retry_never = None
    wait_none = None
else:
    TENACITY_FOUND = True
    from tenacity.retry import retry_any, retry_base, retry_if_result, retry_never
    from tenacity.wait import (
        wait_combine,
        wait_base,
        wait_none,
        wait_random_exponential,
    )


def assert_tenacity_installed():
    """Raise if tenacity is not importable."""
    if not TENACITY_FOUND:
        raise ModuleNotFoundError(
            """
            Could not find the tenacity module! Please reinstall pyairtable
            with the tenacity extra. You can do so with:
                $ pip install pyairtable[tenacity]
            """
        )


def is_rate_limited(response: Response):
    """Return True if rate limited."""
    return response.status_code == 429


class RetryingRequestStrategy(SimpleRequestStrategy):
    """
    Wraps SimpleRequestStrategy to retry requests.

    Accepts a tenacity.Retrying object to configure retry behavior.

    Usage:
        >>> request_strategy = RetryingRequestStrategy()
        >>> api = Api('apikey', request_strategy=request_strategy)
    or:
        >>> retrying = Retrying(stop_after_attempt(3))
        >>> request_strategy = RetryingRequestStrategy(retrying)
        >>> api = Api('apikey', request_strategy=request_strategy)
    or:
        >>> request_strategy = RetryingRequestStrategy(
                stop=stop_after_attempt(3)
            )
        >>> api = Api('apikey', request_strategy=request_strategy)
    """

    _retrying: Retrying

    @overload
    def __init__(self):
        """Initialize with the defaults (retries on failure)."""
        ...

    @overload
    def __init__(self, retrying_: Retrying, session: Optional[Session] = None):
        """Initialize with a Retrying and optionally a Session."""
        ...

    @overload
    def __init__(self, *, retrying_: Retrying, session: Optional[Session] = None):
        """Initialize with Retrying and Session passed as keyword arguments."""
        ...

    @overload
    def __init__(self, *, session: Optional[Session] = None, **kwargs: Any):
        """Initialize with Session and other keyword arguments for Retrying."""
        ...

    @overload
    def __init__(self, **kwargs: Any):
        """Initialize with only keyword arguments for Retrying."""
        ...

    def __init__(
        self,
        retrying_: Optional[Retrying] = None,
        session: Optional[Retrying] = None,
        **kwargs: Any,
    ):
        """
        If tenacity is installed, initialize a retrying strategy.

        Arguments:
            retrying(``Retrying``, optional): |arg_retrying|
            session(``Session``, optional): |arg_session|

        Keyword Arguments:
            **kwargs(``dict``, optional): |kwargs_retrying|
        """
        assert_tenacity_installed()
        super().__init__(session=session)

        if retrying_ is None:
            retrying_ = kwargs.pop("retrying", None)

        if retrying_ is not None:
            if not isinstance(retrying_, Retrying):
                raise TypeError(
                    f"Must provide a Retrying as a strategy! Got {retrying_!r}"
                )
            if kwargs:
                raise ValueError(
                    "Must provide either Retrying instance or Retrying "
                    f"constructor keyword arguments! Got both {retrying_!r} "
                    f"and {kwargs!r}!"
                )
            self.retrying = retrying_
        elif not kwargs:
            raise ValueError(
                "Must provide either Retrying instance or Retrying constructor"
                "keyword arguments! Got neither!"
            )
        self.retrying = self.__class__.make_retrying(**kwargs)

    @property
    def retrying(self) -> Retrying:
        """Return the tenacity.Retrying object that wraps _request."""
        return self._retrying

    if TENACITY_FOUND:

        @retrying.setter
        def retrying(self, retrying: Retrying):
            """Set the tenacity.Retrying and update the wrapped _request()."""
            self._retrying = retrying
            self._retrying_request = retrying.wraps(super()._request)

        def _request(self, method: str, url: str, **kwargs: Any) -> Response:
            """Make requests and retry based on the response code."""
            if self._retrying_request is None:
                return self._request(method, url, **kwargs)
            return self._retrying_request(method, url, **kwargs)

    @staticmethod
    def make_retrying(*, retry: retry_base = None, wait: wait_base = None, **kwargs):
        """
        Create a retrying object.

        Sugar to bypass the need to importing Retrying. Passes any keyword
        arguments to the Retrying constructor.

        Keyword Arguments:
            **kwargs(``dict``, optional): |kwargs_retrying|
        """
        assert_tenacity_installed()
        return Retrying(retry=retry, wait=wait, **kwargs)


class RateLimitRetryingRequestStrategy(RetryingRequestStrategy):
    """
    Wraps SimpleRequestStrategy to retry requests based on response code.

    Airtable responds with a 429 if a request fails due to exceeding rate
    limits. We can implement the strategy used by the official airtable.js and
    retry with exponential and jittered backoff. See
    https://github.com/Airtable/airtable.js/blob/9d40666979af77de9546d43177cab086a03028bf/src/run_action.ts#L70-L75

    The API requires a wait of 30s after the rate limits are exceeded.

    Keyword arguments passed to the constructor are combined with those needed
    to implement the rate-limit respective behavior.

    Usage:
        >>> request_strategy = RateLimiRetryingRequestStrategy()
        >>> api = Api('apikey', request_strategy=request_strategy)
    or:
        >>> request_strategy = RateLimiRetryingRequestStrategy(
                stop=stop_after_attempt(3)
            )
        >>> api = Api('apikey', request_strategy=request_strategy)
    """

    def __init__(self, session: Optional[Session] = None, **kwargs: Any):
        """
        If tenacity is installed, initialize a retrying strategy that mimics
        the retrying behavior of the offial airtable.js library.

        NB: Unlike RetryingRequestStrategy, this constructor does not accept a
        Retrying instance as a parameter.

        Arguments:
            session(``Session``, optional): |arg_session|

        Keyword Arguments:
            **kwargs(``dict``, optional): |kwargs_retrying|
        """
        assert_tenacity_installed()
        if any(
            (
                isinstance(session, Retrying),
                kwargs.get("retrying_", None) is not None,
                kwargs.get("retrying", None) is not None,
            )
        ):
            raise ValueError(
                "RateLimiRetryingRequestStrategy does not accept a Retrying "
                "instance as an argument!"
            )

        super().__init__(session=session, **kwargs)

    @staticmethod
    def make_retrying(
        *,
        retry: retry_base = retry_never,
        wait: wait_base = wait_none,
        **kwargs,
    ):
        """
        Create a retrying object with rate limiting behavior.

        Sugar to bypass the need to importing Retrying. Passes any keyword
        arguments to the Retrying constructor.

        See:
            https://tenacity.readthedocs.io/en/latest/api.html#tenacity.Retrying

        Keyword Arguments:
            retry(``tenacit.retry_base``, optional):
                Additional retry conditions to be combined with the condition
                of retrying on 429 response codes.
            wait(``tenacit.wait_base``, optional):
                Additional wait time that will be added to the wait time
                imposed by the 5s exponential backoff as used by the
                airtable.js library.
            **kwargs(``dict``, optional): Keyword arguments for Retrying()

        See:
            https://tenacity.readthedocs.io/en/latest/api.html#tenacity.Retrying
        """
        assert_tenacity_installed()
        backoff = wait_random_exponential(multiplier=5, max=600)
        return super().make_retrying(
            retry=retry_any(retry, retry_if_result(is_rate_limited)),
            wait=wait_combine(wait, backoff),
            **kwargs,
        )
