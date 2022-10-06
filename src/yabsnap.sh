#!/bin/bash

set -ueo pipefail

readonly MY_PATH="$(dirname "$(realpath "$0")")"

cd $MY_PATH
python3 -m code.main "$@"
