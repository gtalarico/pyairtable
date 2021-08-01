.PHONY: test docs

usage:
	cat Makefile

release:
	python setup.py sdist bdist_wheel --universal
	twine upload ./dist/*
	make clean

test:
	pytest -v

tox:
	tox -e py

coverage:
	pytest --cov=airtable --cov-report=html
	open htmlcov/index.html

lint:
	flake8 .
	black --diff .

docs:
	bash -c "cd ./docs; make html"
	# open ./docs/build/html/index.html

clean:
	python3 -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	python3 -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('pytest_cache')]"
	rm -rdf ./docs/build
	rm -rdf ./dist
	rm -rdf ./build
	rm -rdf  airtable_python_wrapper.egg-info

