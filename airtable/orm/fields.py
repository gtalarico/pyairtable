import re
from typing import Any, TypeVar, Union, Type, Generic, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from airtable.orm import Model  # noqa

T_Linked = TypeVar("T_Linked", bound="Model")


class FieldDescriptor:
    def __init__(self, field_name, validate=True) -> None:
        self.field_name = field_name
        self.validate = validate

    def __set__(self, instance, value):
        if self.validate and not self.is_valid(value):
            raise TypeError("value '{}' invalid for field '{}'".format(value, self))
        instance._fields[self.field_name] = value

    def is_valid(self, value) -> bool:
        return True

    def __get__(self, instance: Any, cls: Any = None) -> Any:
        raise NotImplementedError()


class LinkField(FieldDescriptor, Generic[T_Linked]):
    def __init__(
        self, field_name, model: Type[T_Linked], lazy=True, validate=True
    ) -> None:
        self._model = model
        self._lazy = lazy
        super().__init__(field_name, validate=validate)

    def __get__(self, instance: Any, cls=None) -> Optional[T_Linked]:

        if not instance:
            raise ValueError("cannot access descriptors on class")

        link_ids = instance._fields.get(self.field_name, [])

        for link_id in link_ids:
            if self._lazy:
                link_instance = self._model()
                link_instance.id = link_id
            else:
                link_record = instance.get_table().get(link_id)
                link_instance = self._model.from_record(link_record)

            return link_instance

        return None


class TextField(FieldDescriptor):
    def __get__(self, instance: Any, cls: Any = None) -> str:
        if not instance:
            raise ValueError("cannot access descriptors on class")
        return instance._fields.get(self.field_name, "")

    def is_valid(self, value) -> bool:
        return isinstance(value, str)


class NumberField(FieldDescriptor):
    def __get__(self, instance: Any, cls: Any = None) -> Union[float, int, None]:
        if not instance:
            raise ValueError("cannot access descriptors on class")
        return instance._fields.get(self.field_name, None)

    def is_valid(self, value) -> bool:
        return isinstance(value, (float, bool))


class BooleanField(FieldDescriptor):
    def __get__(self, instance: Any, cls: Any = None) -> Optional[bool]:
        if not instance:
            raise ValueError("cannot access descriptors on class")
        return instance._fields.get(self.field_name, None)


class EmailField(FieldDescriptor):
    def __get__(self, instance: Any, cls: Any = None) -> Optional[str]:
        if not instance:
            raise ValueError("cannot access descriptors on class")
        return instance._fields.get(self.field_name, None)

    def is_valid(self, value):
        regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        return bool(re.match(regex, value))
