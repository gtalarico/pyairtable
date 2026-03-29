#!/bin/zsh

function fail {
    echo "$@" >&2
    exit 1
}

function confirm_eval {
    command=($@)
    echo "% ${(q)command[@]}"
    read -k "confirm?Run? [y/n] "; echo
    [[ ! "$confirm" =~ [yY] ]] && fail "Cancelled."
    eval "${(q)command[@]}"
}

function bump {
    current_version=$(python3 -c 'from pyairtable import __version__; print(__version__)')
    read "release_version?Release version [$current_version]: "
    if [[ -z "$release_version" ]]; then
        release_version=$current_version
    elif [[ "$release_version" != "$current_version" ]]; then
        sed -i "" "s/^__version__ = .*$/__version__ = \"$release_version\"/" pyairtable/__init__.py
        git add pyairtable/__init__.py
        PAGER=cat git status
        PAGER=cat git diff --cached pyairtable/__init__.py
        confirm_eval git commit -m "Release $release_version" pyairtable/__init__.py
    fi
}

function push {
    endpoint=gtalarico/pyairtable
    origin=$(git remote -v | grep $endpoint | grep '\(push\)' | awk '{print $1}')
    if [[ -z "$origin" ]]; then
        fail "no remote matching $endpoint"
    fi
    confirm_eval git tag -s -m "Release $release_version" $release_version
    confirm_eval git push $origin $release_version
}

bump
push
