from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Iterable, Mapping, Optional, Text, Tuple, Type, Union

from requests import Response
from requests.exceptions import HTTPError

Headers = Union[Mapping[str, Text], Iterable[Tuple[str, Text]]]


def process_response(response: Response) -> Any:
    """Process a Response to return the body or raise any errors with it."""
    try:
        response.raise_for_status()
    except HTTPError as exc:
        err_msg = str(exc)

        # Attempt to get Error message from response, Issue #16
        try:
            error_dict = response.json()
        except ValueError:
            pass
        else:
            if "error" in error_dict:
                err_msg += " [Error: {}]".format(error_dict["error"])
        exc.args = (*exc.args, err_msg)
        raise exc
    else:
        return response.json()


class RequestStrategy(metaclass=ABCMeta):
    """Abstract request strategy."""

    session: Any

    @abstractmethod
    def request(
        self,
        method: str,
        url: str,
        params: Dict[str, Any],
        json: Dict[str, Any],
        timeout: Optional[Tuple[int, int]],
        headers: Headers,
    ) -> Any:
        """Must provide a request method."""
        ...

    @classmethod
    def initialize(
        cls, request_strategy: Union[Type["RequestStrategy"], "RequestStrategy"]
    ) -> "RequestStrategy":
        """Init if a subclass, return if an instance, else raise."""
        if isinstance(request_strategy, type) and issubclass(
            request_strategy, RequestStrategy
        ):
            request_strategy = request_strategy()
        elif not isinstance(request_strategy, RequestStrategy):
            raise TypeError(
                "Error! request_strategy must either be a subclass of "
                "RequestStrategy or an instance of one! "
                f"(got: `{request_strategy!r}`)"
            )
        return request_strategy
