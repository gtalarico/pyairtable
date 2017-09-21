"""
Airtable Parameter Filters

"""  #


class _BaseParam():

    def __init__(self, value):
        self.value = value

    def to_param_dict(self):
        return {self.param_name: self.value}


class _BaseStringArrayParam(_BaseParam):
    """
    Api Expects Array Of Strings:
    >>> ['FieldOne', 'Field2']

    Requests Params Input:
    >>> params={'fields': ['FieldOne', 'FieldTwo']}

    Requests Url Params Encoding:
    >>> ?fields=FieldOne&fields=FieldTwo

    Expected Url Params:
    >>> ?fields[]=FieldOne&fields[]=FieldTwo
    """

    def to_param_dict(self):
        encoded_param = self.param_name + '[]'
        return {encoded_param: self.value}


class _BaseObjectArrayParam(_BaseParam):
    """
    Api Expects Array of Objects:
    >>> [{field: "UUID", direction: "desc"}, {...}]

    Requests Params Input:
    >>> params={'sort': ['FieldOne', '-FieldTwo']}
    or
    >>> params={'sort': [('FieldOne', 'asc'), ('-FieldTwo', 'desc')]}

    Requests Url Params Encoding:
    >>> ?sort=field&sort=direction&sort=field&sort=direction

    Expected Url Params:
    >>> ?sort[0][field]=FieldOne&sort[0][direction]=asc
    """

    def to_param_dict(self):
        param_dict = {}
        for index, dictionary in enumerate(self.value):
            for key, value in dictionary.items():
                param_name = '{param_name}[{index}][{key}]'.format(
                                                    param_name=self.param_name,
                                                    index=index,
                                                    key=key)
                param_dict[param_name] = value
        return param_dict


class AirtableParams():

    class MaxRecordsParam(_BaseParam):
        param_name = 'maxRecords'
        kwarg = 'max_records'

    class ViewParam(_BaseParam):
        param_name = 'view'
        kwarg = param_name

    class PageSizeParam(_BaseParam):
        param_name = 'pageSize'
        kwarg = 'page_size'

    class FormulaParam(_BaseParam):
        param_name = 'filterByFormula'
        kwarg = 'formula'

        @classmethod
        def and_formula(cls, *formulas):
            combined_formula = 'AND({})'.format(','.format(*formulas))
            super(FormulaParam, self).__init__(combined_formula)

    class OffsetParam(_BaseParam):
        param_name = 'offset'
        kwarg = param_name

    class FieldsParam(_BaseStringArrayParam):
        """
        Fields Param

        Usage:
            >>> param = FieldsParam(['FieldOne', 'FieldTwo'])
            >>> param.to_param_dict()
            {'fields[]': ['FieldOne', 'FieldTwo']}
        """
        param_name = 'fields'
        kwarg = param_name

    class SortParam(_BaseObjectArrayParam):
        """
        Sort Filter

        Usage:
            >>> filter = SortParam([{'field': 'col', 'direction': 'asc'}])
            >>> filter.to_param_dict()
            {'sort[0]['field']: 'col', sort[0]['direction']: 'asc'}
        """

        param_name = 'sort'
        kwarg = param_name

        def __init__(self, value):
            # Wraps string into list to avoid string iteration
            if hasattr(value, 'startswith'):
                value = [value]

            self.value = []
            direction = 'asc'

            for item in value:
                if not hasattr(item, 'startswith'):
                    field_name, direction = item
                else:
                    if item.startswith('-'):
                        direction = 'desc'
                        field_name = item[1:]
                    else:
                        field_name = item

                sort_param = {'field': field_name, 'direction': direction}
                self.value.append(sort_param)

    @classmethod
    def _discover_params(cls):
        """ Returns a dict where filter keyword is key, and class is value """
        try:
            return cls.filters
        except AttributeError:
            filters = {}
            for param_class_name in dir(cls):
                param_class = getattr(cls, param_class_name)
                if hasattr(param_class, 'kwarg'):
                    filters[param_class.kwarg] = param_class
                    filters[param_class.param_name] = param_class
            cls.filters = filters
        return cls.filters

    @classmethod
    def get(cls, kwarg_name):
        """ Returns a Param Class Instance, by its keyword name """
        param_classes = cls._discover_params()
        try:
            param_class = param_classes[kwarg_name]
        except KeyError:
            raise ValueError('invalid param keyword {}'.format(kwarg_name))
        else:
            return param_class
