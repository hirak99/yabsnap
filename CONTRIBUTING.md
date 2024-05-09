# How to Contribute

We'd love to accept your patches and contributions to this project. There are
just a few small guidelines you need to follow.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution;
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

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
- [pyright](https://microsoft.github.io/pyright/#/)
  ([AUR](https://archlinux.org/packages/extra/any/pyright/)) for linting,
- [mypy](https://mypy-lang.org/)
  ([AUR](https://archlinux.org/packages/extra/any/mypy/)) for static type
  checking, and
- [black](https://github.com/psf/black)
  ([AUR](https://archlinux.org/packages/extra/any/python-black/)) for
  formatting.

Before creating a pull request, please run the following tests locally -
- `src/run_full_tests.sh` - Unit tests and linting / formatting checks.
- `scripts/scripts/test_install-to-dest.sh` - Tests the installation script.

