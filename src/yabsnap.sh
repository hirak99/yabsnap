set -ueo pipefail

readonly MY_PATH=$(cd $(dirname "$0") && pwd)

cd ${MY_PATH}
python3 -m code.snap $@

