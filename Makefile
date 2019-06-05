.PHONY: test docs

# Colors
NC=\x1b[0m
L_GREEN=\x1b[32;01m

## usage: print useful commands
usage:
	@echo "$(L_GREEN)Choose a command: $(PWD) $(NC)"
	@bash -c "sed -ne 's/^##//p' ./Makefile | column -t -s ':' |  sed -e 's/^/ /'"

## deploy: Deploy
deploy:
	python setup.py sdist bdist_wheel --universal
	twine upload ./dist/*
	make clean

## test: Run tests
test:
	tox
	make clean

## lint: Lint and format
lint:
	flake8 .
	black --check .

## docs: Generate docs locally
docs:
	bash -c "cd ./docs; make html"
	open ./docs/build/html/index.html


## clean: delete python artifacts
clean:
	python3 -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
	python3 -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('pytest_cache')]"
	rm -rdf ./docs/build
	rm -rdf ./dist
	rm -rdf ./build
	rm -rdf  airtable_python_wrapper.egg-info

