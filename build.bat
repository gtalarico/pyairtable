python setup.py sdist bdist_wheel --universal
twine upload dist\*
rmdir /S dist\
rmdir /S build\
rmdir /S airtable_python_wrapper.egg-info
