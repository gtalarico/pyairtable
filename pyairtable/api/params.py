from typing import List, Dict, Any
from collections import OrderedDict


class InvalidParamException(ValueError):
    """Raise when invalid parameters are used"""

    def __init__(self, message, *args):
        self.message = message
        super().__init__(message, *args)


def dict_list_to_request_params(param_name: str, values: List[dict]) -> dict:
    """
    Returns dict to be used by request params from dict list

    Expected Airtable Url Params is:
        `?sort[0][field]=FieldOne&sort[0][direction]=asc`

    >>> objects = [
    ...    { "field": "FieldOne", "direction": "asc"},
    ...    { "field": "FieldTwo", "direction": "desc"},
    ... ]
    >>> dict_list_to_request_params("sort", objects)
    {
        "sort[0][field]": "FieldOne",
        "sort[0][direction]: "asc",
        "sort[1][field]": "FieldTwo",
        "sort[1][direction]: "desc",
    }

    """
    param_dict = {}
    for index, dictionary in enumerate(values):
        for key, value in dictionary.items():
            field_name = "{param_name}[{index}][{key}]".format(
                param_name=param_name, index=index, key=key
            )
            param_dict[field_name] = value
    return OrderedDict(sorted(param_dict.items()))


def field_names_to_sorting_dict(field_names: List[str]) -> List[Dict[str, str]]:
    # TODO edge case fields starting with '-'
    """

    >>> field_names_to_sorting_dict(["Name", "-Age"])
    [
        { "field": "FieldOne", "direction": "asc"},
        { "field": "FieldTwo", "direction": "desc"},
    ]
    """
    values = []

    for field_name in field_names:

        if field_name.startswith("-"):
            direction = "desc"
            field_name = field_name[1:]
        else:
            direction = "asc"

        sort_param = {"field": field_name, "direction": direction}
        values.append(sort_param)
    return values


def to_params_dict(param_name: str, value: Any, query=True) -> dict:
    """
    Returns a dictionary representing api params.
    When `query` is True, params returned are for use in query params (param=)
    When False, they are formatted for use in a body payload (json_data=)
    """
    if param_name == "max_records":
        return {"maxRecords": value}
    elif param_name == "view":
        return {"view": value}
    elif param_name == "page_size":
        return {"pageSize": value}
    elif param_name == "offset":
        return {"offset": value}
    elif param_name == "formula":
        return {"filterByFormula": value}
    elif param_name == "fields":
        return {"fields[]": value} if query else {"fields": value}
    elif param_name == "cell_format":
        return {"cellFormat": value}
    elif param_name == "time_zone":
        return {"timeZone": value}
    elif param_name == "user_locale":
        return {"userLocale": value}
    elif param_name == "return_fields_by_field_id":
        return {"returnFieldsByFieldId": int(value) if query else bool(value)}
    elif param_name == "sort":
        value = field_names_to_sorting_dict(value)
        return dict_list_to_request_params("sort", value) if query else {"sort": value}
    else:
        msg = "'{0}' is not a supported parameter".format(param_name)
        raise InvalidParamException(msg)
