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
>>> aitable = Airtable(base_key, table_name)
```

### Get Records

```
# Get Records
>>> airtable.get_records()
[{'fields': {...}}, ...]
# Note: Get methods will return the records as dictionary exact as document in the API

# Get Records - Options
>>> airtable.get_records(view='MyView')
>>> airtable.get_records(maxRecords='MyView')


# Get Match - Returns first match
>>> airtable.get_match('Name', 'Your Name')

# Get Search - Returns all matches in Table
>>> airtable.get_search('Name', 'Your Name')

```

### Create Records

```
# Insert a record
>>> response = airtable.insert({'Name': 'Your Name'})
# Note: All Post/Patch methods will return a request response object
>>> response
<Response: 200>
>>> response.json()
{'id': 'xxx', 'fields': {...}}

# Batch Create
>>> records = [{'Name': 'Your Name'}, {'Name': 'Another Name'}]
airtable.batch_insert(records)
```

### Update

```
# Update a record
>>> response = airtable.update(record_id, {'Name': 'Your Name'})

# Update by field
>>> response = airtable.update_by_field('Name', 'Your Name', {'Name': 'New Name'})
```


# TODO:

- [ ] Implement Delete
- [ ] Implement Filter
- [ ] Implement Sort
- [ ] Finish Docstrings
- [ ] Add Examples
- [ ] Add Sphinx

##### License
[MIT](https://opensource.org/licenses/MIT)
