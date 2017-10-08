"""
Parameter filters are instantiated internally
by using the corresponding keywords.

Filter names (kwargs) can be either the API camelCase name (ie ``maxRecords``)
or the snake-case equivalent (``max_records``).

Refer to the :any:`Airtable` class to verify which kwargs can be
used with each method.

The purpose of these classes is to 1. improve flexibility and
ways in which parameter filter values can be passed, and 2. properly format
the parameter names and values on the request url.

For more information see the full implementation below.

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
        """
        Max Records Param

        Kwargs:
            ``max_records=`` or ``maxRecords=``

        The maximum total number of records that will be returned.

        Usage:

        >>> airtable.get_all(view='My View')

        Args:
            max_records (``int``): The maximum total number of records that
                will be returned.


        """

        # Class Input > Output
        # >>> filter = MaxRecordsParam(100)
        # >>> filter.to_param_dict()
        # {'maxRecords: 100}

        param_name = 'maxRecords'
        kwarg = 'max_records'

    class ViewParam(_BaseParam):
        """
        View Param

        Kwargs:
            ``view=``

        If set, only the records in that view will be returned.
        The records will be sorted according to the order of the view.

        Usage:

        >>> airtable.get_all(view='My View')

        Args:
            view (``str``): The name or ID of a view.

        """

        # Class Input > Output
        # >>> filter = ViewParam('Name or Id Of View')
        # >>> filter.to_param_dict()
        # {'view: 'Name or Id Of View'}

        param_name = 'view'
        kwarg = param_name

    class PageSizeParam(_BaseParam):
        """
        Page Size Param

        Kwargs:
            ``page_size=`` or ``pageSize=``

        Limits the maximum number of records returned in each request.
        Default is 100.

        Usage:

        >>> airtable.get_all(page_size=50)

        Args:
            formula (``int``): The number of records returned in each request.
                Must be less than or equal to 100. Default is 100.

        """
        # Class Input > Output
        # >>> filter = PageSizeParam(50)
        # >>> filter.to_param_dict()
        # {'pageSize: 50}

        param_name = 'pageSize'
        kwarg = 'page_size'

    class FormulaParam(_BaseParam):
        """
        Formula Param

        Kwargs:
            ``formula=`` or ``filterByFormula=``

        The formula will be evaluated for each record, and if the result
        is not 0, false, "", NaN, [], or #Error! the record will be included
        in the response.

        If combined with view, only records in that view which satisfy the
        formula will be returned. For example, to only include records where
        ``COLUMN_A`` isn't empty, pass in: ``"NOT({COLUMN_A}='')"``

        For more information see
        `Airtable Docs on formulas. <https://airtable.com/api>`_

        Usage - Text Column is not empty:

        >>> airtable.get_all(formula="NOT({COLUMN_A}='')")

        Usage - Text Column contains:

        >>> airtable.get_all(formula="FIND('SomeSubText', {COLUMN_STR})=1")

        Args:
            formula (``str``): A valid Airtable formula.

        """

        # Class Input > Output
        # >>> param = FormulaParams("FIND('DUP', {COLUMN_STR})=1")
        # >>> param.to_param_dict()
        # {'formula': "FIND('WW')=1"}

        param_name = 'filterByFormula'
        kwarg = 'formula'



    class _OffsetParam(_BaseParam):
        """
        Offset Param

        Kwargs:
            ``offset=``

        If there are more records what was in the response,
        the response body will contain an offset value.
        To fetch the next page of records,
        include offset in the next request's parameters.

        This is used internally by :any:`get_all` and :any:`get_iter`.

        Usage:

        >>> airtable.get_iter(offset='recjAle5lryYOpMKk')

        Args:
            record_id (``str``, ``list``):

        """
        # Class Input > Output
        # >>> filter = _OffsetParam('recqgqThAnETLuH58')
        # >>> filter.to_param_dict()
        # {'offset: 'recqgqThAnETLuH58'}

        param_name = 'offset'
        kwarg = param_name

    class FieldsParam(_BaseStringArrayParam):
        """
        Fields Param

        Kwargs:
            ``fields=``

        Only data for fields whose names are in this list will be included in
        the records. If you don't need every field, you can use this parameter
        to reduce the amount of data transferred.

        Usage:

        >>> airtable.get(fields='ColumnA')

        Multiple Columns:

        >>> airtable.get(fields=['ColumnA', 'ColumnB'])

        Args:
            fields (``str``, ``list``): Name of columns you want to retrieve.

        """

        # Class Input > Output
        # >>> param = FieldsParam(['FieldOne', 'FieldTwo'])
        # >>> param.to_param_dict()
        # {'fields[]': ['FieldOne', 'FieldTwo']}

        param_name = 'fields'
        kwarg = param_name

    class SortParam(_BaseObjectArrayParam):
        """
        Sort Param

        Kwargs:
            ``sort=``

        Specifies how the records will be ordered. If you set the view
        parameter, the returned records in that view will be sorted by these
        fields.

        If sorting by multiple columns, column names can be passed as a list.
        Sorting Direction is ascending by default, but can be reversed by
        prefixing the column name with a minus sign ``-``, or passing
        ``COLUMN_NAME, DIRECTION`` tuples. Direction options
        are ``asc`` and ``desc``.

        Usage:

        >>> airtable.get(sort='ColumnA')

        Multiple Columns:

        >>> airtable.get(sort=['ColumnA', '-ColumnB'])

        Explicit Directions:

        >>> airtable.get(sort=[('ColumnA', 'asc'), ('ColumnB', 'desc')])

        Args:
            fields (``str``, ``list``): Name of columns and directions.

        """

        # Class Input > Output
        # >>> filter = SortParam([{'field': 'col', 'direction': 'asc'}])
        # >>> filter.to_param_dict()
        # {'sort[0]['field']: 'col', sort[0]['direction']: 'asc'}

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
        """
        Returns a dict where filter keyword is key, and class is value.
        To handle param alias (maxRecords or max_records), both versions are
        added.
        """

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
    def _get(cls, kwarg_name):
        """ Returns a Param Class Instance, by its kwarg or param name """
        param_classes = cls._discover_params()
        try:
            param_class = param_classes[kwarg_name]
        except KeyError:
            raise ValueError('invalid param keyword {}'.format(kwarg_name))
        else:
            return param_class
