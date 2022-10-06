set -ueo pipefail

readonly MY_PATH="$(dirname "$(realpath "$0")")"

cd ${MY_PATH}
pwd
python3 -m code.snap $@

