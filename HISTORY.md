# 0.14.0
* Removed `mirror()` method.
* Feature: Configurable request timeout

# 0.13.0
* Fixed: Python 2 compatibility issues
* Start CI testing on all supported Python versions
* **Breaking**: Drop implicit support for Python 3.4, officially support 3.7 and 3.8.

# 0.12.0
* Fixed: Rewrote tests
* Fixed: Improve CI and deployment

# 0.11.2
* Fixed: Add sdist and universal for 2.7 dist
* Fixed: Long dist set to markdown

# 0.11.0
* Feature: Merged PR#17 - Added typecast to update, update_by_field, replace, replace_by_field

# 0.10.1
* Feature: Added typcase option to batch_insert

# 0.10.0
* Feature: Merged PR#17 - typecase kwarg

# 0.9.1
* Feature: Better exception message for 422 (Issue #16)
* Fix: 2.7 Compat with sys.implementation

# 0.9.0
* Docs: Revised Docs strings to show kebab case kwargs
* Fix: Url Escape (PR#1)

# 0.8.0
* Docs: New Documentation on Parameter filters Docs
* Docs: More documentation and examples.
* Feature: Search now uses filterByFormula
* Added Formula Generator

# 0.7.3
* Removed Unencoded Debug Msg due to IronPython Bug #242

# 0.7.2
* Merge Fix

# 0.7.1-alpha
* Moved version to sep file to fix setup.py error
* Removed urlencode import
* Added Explicit Raise for 422 errors with Decoded Urls

# 0.7.0-dev1
* Feature: Added airtable.get() method to retrieve record
* Fix: sort/field string input to allow sting or list
* Fix: AirtableAuth Docs
* Fix: Keyargs Docs

# 0.6.1-dev1
* Bugfix: Fix Setup to install six.py
* Bugfix: Fix AitableAuth Docs

# 0.6.0-dev1
* Implemented Sort Filter
* Implemented FilterByFormula
* Implemented all param filters as classes
* Added Aliases for Parameters
* Renamed get() to get_iter()

# 0.5.0-dev1

# 0.4.0
* Added replace()
* Added mirror()

# 0.3.0
* Initial Work
