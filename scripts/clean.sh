#!/bin/bash

echo "Cleaning up bytecode, cache, and build files 🧹"
set -x

python3 -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.py[co]')]"
python3 -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('pytest_cache')]"
rm -rdf ./build
rm -rdf ./dist
rm -rdf ./docs/build
rm -rdf ./htmlcov
rm -rdf .mypy_cache
rm -rdf .pytest_cache
rm -rdf pyairtable.egg-info
