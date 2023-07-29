from typing import Any, Dict, Optional, Union

from pyairtable.api import Api, Base, Table


def get_api_bases(api: Union[Api, Base]) -> Dict[Any, Any]:
    """
    Return list of Bases from an Api or Base instance.
    For More Details `Metadata Api Documentation <https://airtable.com/api/meta>`_

    Args:
        api: :class:`Api` or :class:`Base` instance

    Usage:
        >>> table.get_bases()
        {
            "bases": [
                {
                    "id": "appY3WxIBCdKPDdIa",
                    "name": "Apartment Hunting",
                    "permissionLevel": "create"
                },
                {
                    "id": "appSW9R5uCNmRmfl6",
                    "name": "Project Tracker",
                    "permissionLevel": "edit"
                }
            ]
        }
    """
    api = api.api if isinstance(api, Base) else api
    base_list_url = api.build_url("meta", "bases")
    return {
        "bases": [
            base
            for page in api.iterate_requests("get", base_list_url)
            for base in page.get("bases", [])
        ]
    }


def get_base_schema(base: Union[Base, Table]) -> Dict[Any, Any]:
    """
    Returns Schema of a Base
    For More Details `Metadata Api Documentation <https://airtable.com/api/meta>`_

    Args:
        base: :class:`Base` or :class:`Table` instance

    Usage:
        >>> get_base_schema(base)
        {
            "tables": [
                {
                    "id": "tbltp8DGLhqbUmjK1",
                    "name": "Apartments",
                    "primaryFieldId": "fld1VnoyuotSTyxW1",
                    "fields": [
                        {
                            "id": "fld1VnoyuotSTyxW1",
                            "name": "Name",
                            "type": "singleLineText"
                        },
                        {
                            "id": "fldoaIqdn5szURHpw",
                            "name": "Pictures",
                            "type": "multipleAttachment"
                        },
                        {
                            "id": "fldumZe00w09RYTW6",
                            "name": "District",
                            "type": "multipleRecordLinks"
                        }
                    ],
                    "views": [
                        {
                            "id": "viwQpsuEDqHFqegkp",
                            "name": "Grid view",
                            "type": "grid"
                        }
                    ]
                }
            ]
        }
    """
    base = base.base if isinstance(base, Table) else base
    base_schema_url = base.api.build_url("meta", "bases", base.id, "tables")
    assert isinstance(response := base.api.request("get", base_schema_url), dict)
    return response


def get_table_schema(table: Table) -> Optional[Dict[Any, Any]]:
    """
    Returns the specific table schema record provided by base schema list

    Args:
        table: :class:`Table` instance

    Usage:
        >>> get_table_schema(table)
        {
            "id": "tbltp8DGLhqbUmjK1",
            "name": "Apartments",
            "primaryFieldId": "fld1VnoyuotSTyxW1",
            "fields": [
                {
                    "id": "fld1VnoyuotSTyxW1",
                    "name": "Name",
                    "type": "singleLineText"
                }
            ],
            "views": [
                {
                    "id": "viwQpsuEDqHFqegkp",
                    "name": "Grid view",
                    "type": "grid"
                }
            ]
        }
    """
    base_schema = get_base_schema(table)
    for table_record in base_schema.get("tables", {}):
        assert isinstance(table_record, dict)
        if table.name == table_record["name"]:
            return table_record
    return None
