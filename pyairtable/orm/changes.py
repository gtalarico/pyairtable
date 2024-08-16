from typing import Callable, Iterable, List, SupportsIndex, Union

from typing_extensions import TypeVar

T = TypeVar("T")


class ChangeNotifyingList(List[T]):
    """
    A list that calls a callback any time it is changed. This allows us to know
    if any mutations happened to the lists returned from linked record fields.
    """

    def __init__(self, *args: Iterable[T], on_change: Callable[[], None]) -> None:
        super().__init__(*args)
        self._on_change = on_change

    def __setitem__(self, index: SupportsIndex, value: T) -> None:  # type: ignore[override]
        self._on_change()
        return super().__setitem__(index, value)

    def __delitem__(self, key: Union[SupportsIndex, slice]) -> None:
        self._on_change()
        return super().__delitem__(key)

    def append(self, object: T) -> None:
        self._on_change()
        return super().append(object)

    def insert(self, index: SupportsIndex, object: T) -> None:
        self._on_change()
        return super().insert(index, object)

    def remove(self, value: T) -> None:
        self._on_change()
        return super().remove(value)

    def clear(self) -> None:
        self._on_change()
        return super().clear()

    def extend(self, iterable: Iterable[T]) -> None:
        self._on_change()
        return super().extend(iterable)

    def pop(self, index: SupportsIndex = -1) -> T:
        self._on_change()
        return super().pop(index)
