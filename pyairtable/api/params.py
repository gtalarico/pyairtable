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


def to_params_dict(param_name: str, value: Any):
    """Returns a dictionary for use in Request 'params'"""
    # TODO: timeZone, userLocale
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
        return {"fields[]": value}
    elif param_name == "sort":
        sorting_dict_list = field_names_to_sorting_dict(value)
        return dict_list_to_request_params("sort", sorting_dict_list)
    else:
        msg = "'{0}' is not a supported parameter".format(param_name)
        raise InvalidParamException(msg)
