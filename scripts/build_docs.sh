#!/bin/bash

set -e

sourceDir="docs/source"
buildDir="docs/build"

source ./scripts/console.sh

info 'Building Docs 📚'

python -m sphinx -a -W -E "$sourceDir" "$buildDir"
