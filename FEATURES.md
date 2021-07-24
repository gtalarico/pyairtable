# Next Version Ideas

# 0. Rename lib

It's been suggested renaming lib, to `python-airtable` or similar.
Could be `pyairtable`


### 1. Table vs Base: Allow dynamic table names

Solution:  implement `Base` which requires table name,
and `Table` which takes name on init and holds:

```python
table = Base()
table.get("table_name", "recordId", api_key="key")

# Table
table = Table("table_name", api_key="key")
table.get("recordId")
```


### 2. List - Iterator

Make request iterating more transparent -
Current `get_all` is not clear it will iterate with multiple
requests until all records are fetched.

```python
# Don't love this, interested if there are other nicer patterns for this
result_iterator = table.iterator(*args)
for records in result_iterator:
    ...

# or to fetch all
table.iterator(*args).all()

```

### 3. Querysets
Make tables queryset-like - think django Q() :)

Other Examples:
* https://docs.djangoproject.com/en/3.2/ref/models/querysets/#operators-that-return-new-querysets
* https://pypika.readthedocs.io/en/latest/2_tutorial.html

```python
all_records = table.records.all()
first = table.records.first()
some = table.records.filter()
one = table.get("recordId")
```


### 4. Search / Filtering
Remove search/match in favor of formula based query building

table.list(match=formula) # returns first that match
table.list(filter=formula) # returns all that match

### 5. Formula building
Would be cool to be able to build formulas, although not sure there is an elegant way to support all formulas:
https://support.airtable.com/hc/en-us/articles/203255215-Formula-field-reference

Could maintain binding for all funcs (might be a burden to maintain):

```python
from airtable.functions import Field, All, Or, Find

formula = And(Field("name") == "x", Field("age") == 20) # name is 'x' and age is 20
fromula = Find(Field("name"), "J") # name includes letter J
```

### 6. Meta Api
Could add support for https://airtable.com/api/meta to fetch schemas, etc

### 7. Airtable Models

I have build model classes around tables in a few projects, could be cool to have a paved road for this:

```python
class Person(AirtableModel):
    name: str
    age: int

>>> person = Person(name="x", age=21)
>>> person.save() # calls airtable.insert since it doesnt' have 'id'
>>> person.id
'rec123asda'
person.name = "y"
person.save() # calls airtable.update(rec123asd) because has known id

```


### 8. File Upload
