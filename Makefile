.PHONY: usage
usage:
	@grep '^[^#[:space:]].*:' Makefile | grep -v '^\.PHONY:' | cut -d: -f1

.PHONY: setup hooks
setup: hooks

hooks:
	tox -re pre-commit --notest
	.tox/pre-commit/bin/pre-commit install
	.tox/pre-commit/bin/pre-commit install-hooks

.PHONY: release
release:
	@bash -c "./scripts/release.sh"

.PHONY: test test-e2e coverage lint format docs clean
test:
	tox -- -m 'not integration'

test-e2e:
	tox

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
