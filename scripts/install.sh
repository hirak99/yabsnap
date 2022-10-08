#!/bin/bash

set -uexo pipefail

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd $MY_PATH

./install-to-dest.sh ''
