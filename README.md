# Airtable Python Wrapper

[![Build Status](https://travis-ci.org/gtalarico/airtable-python-wrapper.svg?branch=master)](https://travis-ci.org/gtalarico/airtable-python-wrapper)

Python Airtable Client Wrapper

# Usage

### Installing

`pip install airtable-python-wrapper`

### Getting Started

```
>>> from airtable import Airtable
>>> airtable = Airtable(base_key, table_name, api_key=your_api_key)
>>> # Alternatively, you can set the env variable AIRTABLE_API_KEY and use
>>> airtable = Airtable(base_key, table_name)
```

### Get Records

#### get()


`airtable.get(view='All')`

One Request Max - Up to 100 records.
Returns iterator.

#### get_all()

`records = airtable.get_all(view='All')``

Multiple requests, 100 at time, until all records are retrieved.
Returns all records in a list.

### Get Records

##### airtable.get()

Iterates over all records in batches set by pageSize (default: 100)
```
>>> for records in airtable.get():
>>>     print(records)
[{'fields': {...}}, ...]
[{'fields': {...}}, ...]
```

##### airtable.all()
```
>>> airtable.get_all()
[{'fields': {...}}, ...]
```


# Get Records - Options
>>> airtable.get_all(view='MyView')
>>> airtable.get_all(maxRecords='MyView')


# Get Match - Returns first match
>>> airtable.match('Name', 'Your Name')

# Get Search - Returns all matches in Table
>>> airtable.search('Name', 'Your Name')

```

### Create Records

```
# Insert a record
>>> record = airtable.insert({'Name': 'Your Name'})
# Note: All Post/Patch/Delete methods will return the json data as per the API
>>> record
{'id': 'xxx', 'fields': {...}}

# Batch Create
>>> records = [{'Name': 'Your Name'}, {'Name': 'Another Name'}]
airtable.batch_insert(records)
```

### Update

```
# Update a record
>>> record = airtable.update(record_id, {'Name': 'Your Name'})

# Update by field
>>> record = airtable.update_by_field('Name', 'Your Name', {'Name': 'New Name'})
```

##### License
[MIT](https://opensource.org/licenses/MIT)

#### TODO:

- [ ] Implement Filter
- [ ] Implement Sort
- [ ] Add Sphinx
