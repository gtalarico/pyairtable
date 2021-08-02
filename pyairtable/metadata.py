import posixpath
from typing import Union, Optional
from pyairtable.api import Api, Base, Table


def get_api_bases(api: Union[Api, Base]) -> dict:
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
    base_list_url = posixpath.join(api.API_URL, "meta", "bases")
    return api._request("get", base_list_url)


def get_base_schema(base: Union[Base, Table]) -> dict:
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
    base_schema_url = posixpath.join(
        base.API_URL, "meta", "bases", base.base_id, "tables"
    )
    return base._request("get", base_schema_url)


def get_table_schema(table: Table) -> Optional[dict]:
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
        if table.table_name == table_record["name"]:
            return table_record
    return None
