#!/bin/bash

source ./scripts/console.sh


function bump {
    previousVersion=$( grep '^__version__' pyairtable/__init__.py | sed 's/__version__ = \"\(.*\)\"/\1/' )
    previousVersion=$(echo -n "${previousVersion}")
    info "Enter Version [current is ${previousVersion}]:"
    read version
    if [ -z "$version" ]; then
        info "Empty version string - using existing"
        version="$previousVersion"
        return
    fi
    sed -i "" "s/^__version__ = .*$/__version__ = \"$version\"/" pyairtable/__init__.py
    echo "Bumped __version__ to $version"
}

function confirmEval {
    info "CMD > $1"
    info "ENTER to confirm"
    read foo
    eval $1
}

function push {
    cmd="git commit -am \"Publish Version: $version\""
    confirmEval "$cmd"

    cmd="git tag -m \"Version $version\" $version"
    confirmEval "$cmd"

    cmd="git push --tags origin main"
    confirmEval "$cmd"
}

bump
push
