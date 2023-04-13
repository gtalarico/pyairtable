.PHONY: usage
usage:
	@grep '^[^#[:space:]].*:' Makefile | grep -v '^\.PHONY:' | cut -d: -f1

.PHONY: setup hooks
setup: hooks

hooks:
	tox -re pre-commit --notest
	.tox/pre-commit/bin/pre-commit install
	.tox/pre-commit/bin/pre-commit install-hooks

.PHONY: release release-test bump
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

.PHONY: test test-e2e tox coverage lint format docs clean
test:
	tox -e py

test-e2e:
	tox -e py -- ""

tox: test

coverage:
	tox -e coverage
	open htmlcov/index.html

lint: format

format:
	tox -e pre-commit

docs:
	tox -e docs

clean:
	@bash -c "./scripts/clean.sh"
