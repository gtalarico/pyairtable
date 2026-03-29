from contextlib import contextmanager
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Iterable,
    Iterator,
    List,
    Optional,
    SupportsIndex,
    Union,
    overload,
)

from typing_extensions import Self, TypeVar

from pyairtable.api.types import AttachmentDict, CreateAttachmentDict
from pyairtable.exceptions import ReadonlyFieldError, UnsavedRecordError

T = TypeVar("T")


if TYPE_CHECKING:
    # These would be circular imports if not for the TYPE_CHECKING condition.
    from pyairtable.orm.fields import AnyField
    from pyairtable.orm.model import Model


class ChangeTrackingList(List[T]):
    """
    A list that keeps track of when its contents are modified. This allows us to know
    if any mutations happened to the lists returned from linked record fields.
    """

    def __init__(self, *args: Iterable[T], field: "AnyField", model: "Model") -> None:
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
        try:
            if not self._tracking_enabled:
                return
        except AttributeError:
            # This means we're being unpickled and won't call __init__.
            return
        self._model._changed[self._field.field_name] = True

    @overload
    def __setitem__(self, index: SupportsIndex, value: T, /) -> None: ...

    @overload
    def __setitem__(self, key: slice, value: Iterable[T], /) -> None: ...

    def __setitem__(
        self,
        index: Union[SupportsIndex, slice],
        value: Union[T, Iterable[T]],
        /,
    ) -> None:
        self._on_change()
        return super().__setitem__(index, value)  # type: ignore

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


class AttachmentsList(ChangeTrackingList[Union[AttachmentDict, CreateAttachmentDict]]):
    def upload(
        self,
        filename: Union[str, Path],
        content: Optional[Union[str, bytes]] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """
        Upload an attachment to the Airtable API and refresh the field's values.

        This method will replace the current list with the response from the server,
        which will contain a list of :class:`~pyairtable.api.types.AttachmentDict` for
        all attachments in the field (not just the ones uploaded).

        You do not need to call :meth:`~pyairtable.orm.Model.save`; the new attachment
        will be saved immediately. Note that this means any other unsaved changes to
        this field will be lost.

        Example:
            >>> model.attachments.upload("example.jpg", b"...", "image/jpeg")
            >>> model.attachments[-1]["filename"]
            'example.jpg'
            >>> model.attachments[-1]["url"]
            'https://v5.airtableusercontent.com/...'
        """
        if not self._model.id:
            raise UnsavedRecordError("cannot upload attachments to an unsaved record")
        if self._field.readonly:
            raise ReadonlyFieldError("cannot upload attachments to a readonly field")
        response = self._model.meta.table.upload_attachment(
            self._model.id,
            self._field.field_name,
            filename=filename,
            content=content,
            content_type=content_type,
        )
        attachments = list(response["fields"].values()).pop(0)
        with self.disable_tracking():
            self.clear()
            # We only ever expect one key: value in `response["fields"]`.
            # See https://airtable.com/developers/web/api/upload-attachment
            self.extend(attachments)
