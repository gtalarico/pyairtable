from typing import Any, TypeVar, Type, Generic, Optional, List, TYPE_CHECKING

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

    def __repr__(self):
        return "<{} field_name='{}'>".format(self.__class__.__name__, self.field_name)


class TextField(Field):
    """Text Field"""

    def __get__(self, *args, **kwargs) -> Optional[str]:
        return super().__get__(*args, **kwargs)


class IntegerField(Field):
    def __get__(self, *args, **kwargs) -> Optional[int]:
        return super().__get__(*args, **kwargs)


class FloatField(Field):
    """Float Field"""

    def __get__(self, *args, **kwargs) -> Optional[float]:
        return super().__get__(*args, **kwargs)


class CheckboxField(Field):
    """Checkbox Field"""

    def __get__(self, *args, **kwargs) -> Optional[bool]:
        return super().__get__(*args, **kwargs)


class EmailField(Field):
    """Email Field"""

    def __get__(self, *args, **kwargs) -> Optional[str]:
        return super().__get__(*args, **kwargs)


class LinkField(Field, Generic[T_Linked]):
    """Linked Field"""

    def __init__(self, field_name: str, model: Type[T_Linked], lazy=True) -> None:
        """
        Represents a Linked Column

        Args:
            field_name: Name of Airtable Column
            model: Model of Linked Type. Must be subtype of :any:`Model`
            lazy: Use `True` to load linked model when looking up attribute. `False`
                will create empty object with only `id` but will not fetch fields.

        Usage:
            >>> TODO
        """
        self._model = model
        self._lazy = lazy
        super().__init__(field_name)

    def __get__(self, instance: Any, cls=None) -> List[T_Linked]:
        """
        Gets value of LinkField descriptor.

        Returns:
            List of Link Instances
        """
        if not instance:
            raise ValueError("cannot access descriptors on class")

        assert hasattr(instance, "get_table"), "instance be subclassed from Model"

        link_ids = instance._fields.get(self.field_name, [])

        instances = []
        for link_id in link_ids:

            # If cache, previous instance is used
            # This is needed to prevent loading a new instance on each attribute lookup
            cached_instance = instance._linked_cache.get(link_id)
            if cached_instance:
                instances.append(cached_instance)
                continue
            else:
                # If Lazy, create empty from model class and set id
                # If not Lazy, fetch record from airtable and create new model instance
                should_fetch = not self._lazy
                new_link_instance = self._model.from_id(link_id, fetch=should_fetch)

                # Cache instance
                instance._linked_cache[link_id] = new_link_instance
                instances.append(new_link_instance)

        return instances

    def __set__(self, instance, value: List[T_Linked]):
        """
        Sets value for LinkField descriptor.
        Value must be list of linked instances - eg:

        >>> contact.address = [address]
        """
        assert hasattr(value, "__iter__"), "LinkField value must be iterable"
        for model_instance in value:
            assert isinstance(model_instance, self._model), "must be model intance"
            # Store instance in cache and store id
            instance._linked_cache[model_instance.id] = model_instance
        ids = [i.id for i in value]
        super().__set__(instance, ids)


class MultipleLinkField(Field, Generic[T_Linked]):
    """Multiple Link Field"""

    # TODO


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
