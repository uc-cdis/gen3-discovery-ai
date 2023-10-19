#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR/.." || fail
pytest -vv --cov-config=.coveragerc --cov=gen3discoveryai --cov-report term-missing:skip-covered --cov-fail-under 95 --cov-report html:_coverage --cov-branch