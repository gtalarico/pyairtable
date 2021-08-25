.PHONY: test docs setup

usage:
	cat Makefile

setup:
	git config core.hooksPath scripts/githooks
	pip install -e .
	pip install -r requirements-test.txt -r requirements-dev.txt

release:
	make clean
	python -m build --sdist --wheel --outdir ./dist
	twine upload ./dist/*

release-test:
	make clean
	python -m build --sdist --wheel --outdir ./dist
	twine upload --repository testpypi ./dist/*

bump:
	@bash -c "./scripts/bump.sh"

test:
	pytest -v -m 'not integration'

test-e2e:
	pytest -v

tox:
	tox -e py

coverage:
	pytest --cov=pyairtable --cov-report=html
	open htmlcov/index.html

lint:
	flake8 .
	black --diff .

format:
	black .

docs:
	@bash -c "./scripts/build_docs.sh"

clean:
	@bash -c "./scripts/clean.sh"

