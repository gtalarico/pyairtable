python setup.py bdist_wheel
twine upload dist\*
rmdir /S dist\
rmdir /S build\
rmdir /S airtable_python_wrapper.egg-info
