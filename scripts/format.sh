#!/bin/bash

set -e

source ./scripts/console.sh

info 'Formatting'

flake8 .
black --diff .
