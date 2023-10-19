#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

echo ----------------------------------------------
echo Running black to automatically format Python
echo ----------------------------------------------
echo    Command: black $SCRIPT_DIR --config $SCRIPT_DIR/.github/linters/.python-black
black $SCRIPT_DIR --config $SCRIPT_DIR/.github/linters/.python-black
echo
echo ----------------------------------------------
echo Running isort to automatically sort imports
echo ----------------------------------------------
echo    Command: isort $SCRIPT_DIR --settings $SCRIPT_DIR/.github/linters
isort $SCRIPT_DIR --settings $SCRIPT_DIR/.github/linters
echo
echo ----------------------------------------------
echo Running pylint to detect lint
echo ----------------------------------------------
echo    Command: pylint -vv $SCRIPT_DIR/gen3discoveryai --rcfile $SCRIPT_DIR/linters/.python-lint
pylint -vv $SCRIPT_DIR/gen3discoveryai --rcfile $SCRIPT_DIR/.github/linters/.python-lint