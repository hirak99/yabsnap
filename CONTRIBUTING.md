# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Code Reviews

All submissions, including submissions by project members, require review. We
use GitHub pull requests for this purpose. Consult
[GitHub Help](https://help.github.com/articles/about-pull-requests/) for more
information on using pull requests.

## Community Guidelines

This project follows [Google's Open Source Community
Guidelines](https://opensource.google/conduct/).

## Prerequisites for Pull Request

This project uses the following for maintaining code styling, which you may
install for ease of development.

Respective configurations, if any, can be found in [pyproject.toml](./pyproject.toml).

| Tool                                              | Purpose              | Visual Studio Code Extensions                                                                            |
| ------------------------------------------------- | -------------------- | -------------------------------------------------------------------------------------------------------- |
| [pyright](https://microsoft.github.io/pyright/#/) | Linting              | [vscode](https://marketplace.visualstudio.com/items?itemName=ms-pyright.pyright)                         |
| [mypy](https://mypy-lang.org/)                    | Static type checking | [vscode](https://marketplace.visualstudio.com/items?itemName=ms-python.mypy-type-checker)                |
| [black](https://github.com/psf/black)             | Formatting           | [vscode](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter) (`Ctrl+Shift+I`) |
| [isort](https://pycqa.github.io/isort/)           | Organizing imports   | [vscode](https://marketplace.visualstudio.com/items?itemName=ms-python.isort) (`Alt+Shift+O`)            |

Before creating a pull request, please run the following tests locally -
- `src/run_full_tests.sh` - Unit tests and linting / formatting checks.
- `scripts/test_install-to-dest.sh` - Tests the installation script.
