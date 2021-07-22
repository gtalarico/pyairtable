from typing import List

from .api import AirtableApi

# from .params import get_param_dict, doc_strings
# from .formulas import field_equals_value


class Base(AirtableApi):
    def __init__(self, base_id, api_key, timeout=None):
        """
        Instantiates a new Airtable Base instance

        >>> table = Airtable('base_id', 'api_key')

        With timeout:

        >>> table = Airtable('base_id', 'tablename', timeout=(1, 1))

        Args:
            base_id(``str``): Airtable base identifier
            api_key (``str``): API key.

        Keyword Args:
            timeout (``int``, ``Tuple[int, int]``, optional): Optional timeout
                parameters to be used in request. `See requests timeout docs.
                <https://requests.readthedocs.io/en/master/user/advanced/#timeouts>`_

        """
        self.base_id = base_id
        super().__init__(api_key, timeout=timeout)

    def get_record_url(self, table_name, record_id):
        return super()._get_record_url(self.base_id, table_name, record_id)

    def get(self, table_name, record_id):
        """
        Retrieves a record by its id

        >>> record = airtable.get('recwPQIfs4wKPyc9D')

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Record
        """
        return super()._get_record(self.base_id, table_name, record_id)

    def get_iter(self, table_name, **options):
        # self, table_name, view="", page_size=None, fields=None, sort=None, formula=""
        """
        Record Retriever Iterator

        |max_records|

        Returns iterator with lists in batches according to pageSize.
        To get all records at once use :any:`get_all`

        >>> for page in airtable.get_iter():
        ...     for record in page:
        ...         print(record)
        [{'fields': ... }, ...]


        |view|
        |page_size|
        |fields|
        |sort|
        |formula|

        Returns:
            iterator (``list``): List of Records, grouped by pageSize

        """
        gen = super()._get_iter(self.base_id, table_name, **options)
        for i in gen:
            yield i

    def first(self, table_name, **options):
        return super()._first(self.base_id, table_name ** options)

    def get_all(self, table_name, **options):
        """
            Retrieves all records repetitively and returns a single list.

            >>> airtable.get_all()
            >>> airtable.get_all(view='MyView', fields=['ColA', '-ColB'])
            >>> airtable.get_all(maxRecords=50)
            [{'fields': ... }, ...]


        Keyword Args:
                |max_records|
                |view|
                |fields|
                |sort|
                |formula|

            Returns:
                records (``list``): List of Records

            >>> records = get_all(maxRecords=3, view='All')

        """
        return super()._get_all(self.base_id, table_name, **options)

    def create(self, table_name, fields, typecast=False):
        """
        Creates a new record

        >>> record = {'Name': 'John'}
        >>> airtable.create(record)

        Args:
            fields(``dict``): Fields to insert.
                Must be dictionary with Column names as Key.

        Keyword Args:
            |typecast|

        Returns:
            record (``dict``): Inserted record

        """

        return super()._create(self.base_id, table_name, fields, typecast=typecast)

    def batch_create(self, table_name, records, typecast=False):
        """
        Breaks records into chunks of 10 and inserts them in batches.
        Follows the set API rate.
        To change the rate limit use ``airtable.API_LIMIT = 0.2``
        (5 per second)

        >>> records = [{'Name': 'John'}, {'Name': 'Marc'}]
        >>> airtable.batch_insert(records)

        Args:
            records(``list``): Records to insert

        Keyword Args:
            |typecast|

        Returns:
            records (``list``): list of added records
        """
        return super()._batch_create(
            self.base_id, table_name, records, typecast=typecast
        )

    def update(
        self,
        table_name: str,
        record_id: str,
        fields: dict,
        replace=False,
        typecast=False,
    ):
        """
        Updates a record by its record id.
        Only Fields passed are updated, the rest are left as is.

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> fields = {'Status': 'Fired'}
        >>> airtable.update(record['id'], fields)

        Args:
            record_id(``str``): Id of Record to update
            fields(``dict``): Fields to update.
                Must be dictionary with Column names as Key

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            |typecast|

        Returns:
            record (``dict``): Updated record
        """

        return super()._update(
            self.base_id,
            table_name,
            record_id,
            fields,
            replace=replace,
            typecast=typecast,
        )

    def batch_update(
        self, table_name: str, records: List[dict], replace=False, typecast=False
    ):
        """
        Updates a records by their record id's in batch.

        Args:
            records(``list``): List of dict: [{"id": record_id, "field": fields_to_update_dict}]

        Keyword Args:
            replace (``bool``, optional): If ``True``, record is replaced in its entirety
                by provided fields - eg. if a field is not included its value will
                bet set to null. If False, only provided fields are updated.
                Default is ``False``.
            |typecast|

        Returns:
            records(``list``): list of updated records
        """
        return super()._batch_update(
            self.base_id, table_name, records, replace=replace, typecast=typecast
        )

    def delete(self, table_name: str, record_id: str):
        """
        Deletes a record by its id

        >>> record = airtable.match('Employee Id', 'DD13332454')
        >>> airtable.delete(record['id'])

        Args:
            record_id(``str``): Airtable record id

        Returns:
            record (``dict``): Deleted Record
        """
        return super()._delete(self.base_id, table_name, record_id)

    def batch_delete(self, table_name: str, record_ids: List[str]):
        """
        Breaks records into batches of 10 and deletes in batches, following set
        API Rate Limit (5/sec).
        To change the rate limit set value of ``airtable.API_LIMIT`` to
        the time in seconds it should sleep before calling the function again.

        >>> record_ids = ['recwPQIfs4wKPyc9D', 'recwDxIfs3wDPyc3F']
        >>> airtable.batch_delete(records_ids)

        Args:
            records(``list``): Record Ids to delete

        Returns:
            records(``list``): list of records deleted

        """
        return super()._batch_delete(self.base_id, table_name, record_ids)

    def __repr__(self) -> str:
        return "<Airtable Base id={}>".format(self.base_id)
