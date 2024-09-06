from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional, SupportsIndex, Union

from typing_extensions import Self, TypeVar

from pyairtable.api.types import AttachmentDict

T = TypeVar("T")


class ChangeTrackingList(List[T]):
    """
    A list that keeps track of when its contents are modified. This allows us to know
    if any mutations happened to the lists returned from linked record fields.
    """

    def __init__(self, *args: Iterable[T], field: Any, model: Any) -> None:
        super().__init__(*args)
        self._field = field
        self._model = model
        self._tracking_enabled = True

    @contextmanager
    def disable_tracking(self) -> Iterator[Self]:
        """
        Temporarily disable change tracking.
        """
        prev = self._tracking_enabled
        self._tracking_enabled = False
        try:
            yield self
        finally:
            self._tracking_enabled = prev

    def _on_change(self) -> None:
        if self._tracking_enabled:
            self._model._changed[self._field.field_name] = True

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


class AttachmentsList(ChangeTrackingList[AttachmentDict]):
    def upload(
        self,
        filename: Union[str, Path],
        content: Optional[bytes] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """
        Upload an attachment to the Airtable API. This will replace the current
        list with the response from the server, which will contain a full list of
        :class:`~pyairtable.api.types.AttachmentDict`.
        """
        if not self._model.id:
            raise ValueError("cannot upload attachments to an unsaved record")
        response = self._model.meta.table.upload_attachment(
            self._model.id,
            self._field.field_name,
            filename=filename,
            content=content,
            content_type=content_type,
        )
        with self.disable_tracking():
            self.clear()
            self.extend(*response["fields"].values())
