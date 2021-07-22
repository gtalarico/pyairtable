from typing import Any, TypeVar, Type, Generic, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from airtable.orm import Model  # noqa

T_Linked = TypeVar("T_Linked", bound="Model")


class Field:
    def __init__(self, field_name) -> None:
        self.field_name = field_name

    def __get__(self, instance, cls=None):
        # Raise if descriptor is called on class, where instance is None
        if not instance:
            raise ValueError("cannot access descriptors on class")

        field_name = self.field_name
        try:
            return instance._fields[field_name]
        except (KeyError, AttributeError):
            return None

    def __set__(self, instance, value):
        if not hasattr(instance, "_fields"):
            instance._fields = {}
        # TODO cast
        instance._fields[self.field_name] = value


class TextField(Field):
    def __get__(self, *args, **kwargs) -> Optional[str]:
        return super().__get__(*args, **kwargs)


class IntegerField(Field):
    def __get__(self, *args, **kwargs) -> Optional[int]:
        return super().__get__(*args, **kwargs)


class FloatField(Field):
    def __get__(self, *args, **kwargs) -> Optional[float]:
        return super().__get__(*args, **kwargs)


class CheckboxField(Field):
    def __get__(self, *args, **kwargs) -> Optional[bool]:
        return super().__get__(*args, **kwargs)


class EmailField(Field):
    def __get__(self, *args, **kwargs) -> Optional[str]:
        return super().__get__(*args, **kwargs)


class LinkField(Field, Generic[T_Linked]):
    def __init__(self, field_name, model: Type[T_Linked], lazy=True) -> None:
        self._model = model
        self._lazy = lazy
        super().__init__(field_name)

    def __get__(self, instance: Any, cls=None) -> Optional[T_Linked]:

        if not instance:
            raise ValueError("cannot access descriptors on class")

        assert hasattr(instance, "get_table"), "instance be subclassed from Model"

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


"""
- [ ] autoNumber
- [ ] barcode
- [ ] button
- [x] checkbox
- [ ] count
- [ ] createdBy
- [ ] createdTime
- [ ] currency
- [ ] date
- [ ] dateTime
- [ ] duration
- [x] email
- [ ] externalSyncSource
- [ ] formula
- [ ] lastModifiedBy
- [ ] lastModifiedTime
- [ ] multilineText
- [ ] multipleAttachments
- [ ] multipleCollaborators
- [ ] multipleLookupValues
- [ ] multipleRecordLinks
- [ ] multipleSelects
- [x] number
- [ ] percent
- [ ] phoneNumber
- [ ] rating
- [ ] richText
- [ ] rollup
- [ ] singleCollaborator
- [x] singleLineText
- [ ] singleSelect
- [ ] url
"""
