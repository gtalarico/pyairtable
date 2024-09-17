"""
pyAirtable can generate ORM models that reflect the schema of an Airtable base.

The simplest way to use this functionality is with the command line utility:

.. code-block::

    % pip install 'pyairtable[cli]'
    % pyairtable base YOUR_BASE_ID orm > your_models.py
"""

import re
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Dict, List, Optional, Sequence, Type

import inflection

from pyairtable.api.base import Base
from pyairtable.api.table import Table
from pyairtable.models import schema as S
from pyairtable.orm import fields

_ANNOTATION_IMPORTS = {
    "date": "from datetime import date",
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "Any": "from typing import Any",
    r"Union\[.+\]": "from typing import Union",
}


class ModelFileBuilder:
    """
    Produces the code for a Python module file that contains ORM classes
    representing all tables in the given base.
    """

    def __init__(
        self,
        base: Base,
        table_ids: Optional[Sequence[str]] = None,
        table_names: Optional[Sequence[str]] = None,
    ):
        """
        Args:
            base: The base to use when inspecting table schemas.
            table_ids: An optional list of table IDs to limit the output.
            table_names: An optional list of table names to limit the output.
        """
        table_ids = table_ids or []
        table_names = table_names or []
        tables = base.tables()
        if table_names or table_ids:
            tables = [t for t in tables if t.name in table_names or t.id in table_ids]
        self.model_builders = [ModelBuilder(self, table) for table in tables]

    @cached_property
    def model_lookup(self) -> Dict[str, "ModelBuilder"]:
        return {
            key: builder
            for builder in self.model_builders
            for key in (builder.table.id, builder.table.name)
        }

    def __str__(self) -> str:
        models_expr = "\n\n\n".join(str(builder) for builder in self.model_builders)
        import_exprs = [
            "import os",
            "from functools import partial",
            *(
                import_text
                for import_expr, import_text in _ANNOTATION_IMPORTS.items()
                if re.search(rf"\[{import_expr}\]", models_expr)
            ),
        ]
        preamble = "\n".join(
            [
                "from __future__ import annotations",
                "",
                *(line for line in import_exprs if line),
                "",
                "from pyairtable.orm import Model",
                "from pyairtable.orm import fields as F",
            ]
        )
        all_expr = "\n".join(
            [
                "__all__ = [",
                *sorted(f"    {b.class_name!r}," for b in self.model_builders),
                "]",
            ]
        )
        return "\n\n\n".join([preamble, models_expr, all_expr])


@dataclass
class ModelBuilder:
    file_generator: ModelFileBuilder
    table: Table
    meta_envvar: str = "AIRTABLE_API_KEY"

    @property
    def field_builders(self) -> List["FieldBuilder"]:
        return [
            FieldBuilder(field_schema, lookup=self.file_generator.model_lookup)
            for field_schema in self.table.schema().fields
        ]

    @property
    def class_name(self) -> str:
        return table_class_name(self.table.schema().name)

    def __str__(self) -> str:
        return "\n".join(
            [
                f"class {self.class_name}(Model):",
                "    class Meta:",
                f"        api_key = partial(os.environ.get, {self.meta_envvar!r})",
                f"        base_id = {self.table.base.id!r}",
                f"        table_name = {self.table.schema().name!r}",
                "",
                *(f"    {fg}" for fg in self.field_builders),
            ]
        )


@dataclass
class FieldBuilder:
    schema: S.FieldSchema
    lookup: Dict[str, ModelBuilder]

    @property
    def var_name(self) -> str:
        return field_variable_name(self.schema.name)

    @property
    def field_class(self) -> Type[fields.AnyField]:
        field_type = self.schema.type
        if isinstance(self.schema, (S.FormulaFieldSchema, S.RollupFieldSchema)):
            if self.schema.options.result:
                field_type = self.schema.options.result.type
        if isinstance(self.schema, S.MultipleRecordLinksFieldSchema):
            try:
                self.lookup[self.schema.options.linked_table_id]
            except KeyError:
                return fields._ListField
        return fields.FIELD_TYPES_TO_CLASSES[field_type]

    def __str__(self) -> str:
        args: List[Any] = [self.schema.name]
        kwargs: Dict[str, Any] = {}
        generic = ""
        cls = self.field_class

        if isinstance(self.schema, S.MultipleLookupValuesFieldSchema):
            generic = lookup_field_type_annotation(self.schema)

        if cls is fields.LinkField:
            assert isinstance(self.schema, S.MultipleRecordLinksFieldSchema)
            linked_model = self.lookup[self.schema.options.linked_table_id]
            kwargs["model"] = linked_model.class_name
            generic = repr(linked_model.class_name)

        if cls is fields._ListField:
            generic = "str"

        if self.schema.type in ("formula", "rollup"):
            assert isinstance(self.schema, (S.FormulaFieldSchema, S.RollupFieldSchema))
            cls = fields.Field
            if self.schema.options.result:
                cls = fields.FIELD_TYPES_TO_CLASSES[self.schema.options.result.type]
            kwargs["readonly"] = True

        generic = generic and f"[{generic}]"
        args_repr = [repr(arg) for arg in args]
        args_repr.extend(f"{k}={v!r}" for (k, v) in kwargs.items())
        args_join = ", ".join(args_repr)
        return f"{self.var_name} = F.{cls.__name__}{generic}({args_join})"


def table_class_name(table_name: str) -> str:
    """
    Convert an Airtable table name into a Python class name.
    """
    name = inflection.singularize(table_name)
    name = re.sub(r"[^a-zA-Z0-9]+", " ", name).strip()
    name = re.sub(r"([0-9]) +([0-9])", r"\1_\2", name)
    name = re.sub(r"^([0-9])", r"_\1", name)
    return "".join(part.capitalize() for part in name.split())


def field_variable_name(field_name: str) -> str:
    """
    Convert an Airtable field name into a Python variable name.
    """
    name = re.sub(r"[^a-zA-Z0-9]+", " ", field_name)
    name = name.strip().lower().replace(" ", "_")
    name = re.sub(r"([0-9]) +([0-9])", r"\1_\2", name)
    name = re.sub(r"^([0-9])", r"_\1", name)
    return name


def lookup_field_type_annotation(schema: S.MultipleLookupValuesFieldSchema) -> str:
    """
    Given the schema for a multipleLookupValues field, determine the type annotation
    we should use when creating the field descriptor.
    """
    if not schema.options.result:
        return "Any"
    lookup_type = schema.options.result.type
    if lookup_type == "multipleRecordLinks":
        return "str"  # otherwise this will be 'list'
    cls = fields.FIELD_TYPES_TO_CLASSES[lookup_type]
    if isinstance(contained_type := getattr(cls, "contains_type", None), type):
        return contained_type.__name__
    valid_types = _flatten(cls.valid_types)
    if len(valid_types) == 1:
        return valid_types[0].__name__
    return "Union[%s]" % ", ".join(t.__name__ for t in _flatten(cls.valid_types))


def _flatten(class_info: fields._ClassInfo) -> List[Type[Any]]:
    """
    Given a _ClassInfo tuple (which can contain multiple levels of nested tuples)
    return a single list of all the actual types contained.
    """
    if isinstance(class_info, type):
        return [class_info]
    flattened = [t for t in class_info if isinstance(t, type)]
    for t in class_info:
        if isinstance(t, tuple):
            flattened.extend(_flatten(t))  # pragma: no cover
    return flattened
