.PHONY: usage
usage:
	@grep '^[^#[:space:]].*:' Makefile | grep -v '^\.PHONY:' | cut -d: -f1

.PHONY: setup hooks
setup: hooks

hooks:
	@(git config --local core.hooksPath && git config --unset core.hooksPath) || true
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
	pytest -v -m 'not integration'

test-e2e:
	pytest -v

tox:
	tox -e py

coverage:
	pytest --cov=pyairtable --cov-report=html
	open htmlcov/index.html

lint:
	mypy pyairtable
	flake8 .
	black --diff .

format:
	tox -e pre-commit

docs:
	tox -e docs

clean:
	@bash -c "./scripts/clean.sh"
