#!/bin/bash

source ./scripts/console.sh

info "Cleanning up files 🧹"

python3 -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
python3 -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('pytest_cache')]"
rm -rdf ./docs/build
rm -rdf ./dist
rm -rdf ./build
rm -rdf ./htmlcov
rm -rdf  pyairtable.egg-info
rm -rdf  .pytest_cache
