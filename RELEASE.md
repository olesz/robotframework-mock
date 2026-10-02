# Release Guide

Releases are published to PyPI automatically by the
[`pypi-publish.yml`](.github/workflows/pypi-publish.yml) workflow when a tag
matching `v*` is pushed.

## Prerequisites

One-time setup:

1. A [PyPI](https://pypi.org/account/register/) account with access to the
   `robotframework-mock` project.
2. A `PYPI_API_TOKEN` repository secret
   (Settings → Secrets and variables → Actions). The workflow authenticates as
   `__token__` using this value; without it the build succeeds and the upload
   step fails.
3. For manual or test releases only:
   ```bash
   pip install build twine
   ```

## Where the version lives

The version is declared in **one place**, `setup.cfg`:

```ini
[metadata]
name = robotframework-mock
version = 0.4.0
```

The published version is taken from this file, **not** from the git tag. The tag
is only the trigger. Always make the tag match `setup.cfg`, or you will publish
a version that does not correspond to the tag name.

## Releasing

### 1. Bump the version

Edit `version` in `setup.cfg` following [semantic versioning](https://semver.org/):

- **patch** (`0.4.0` → `0.4.1`) — bug fixes only
- **minor** (`0.4.0` → `0.5.0`) — new backwards-compatible features
- **major** (`0.4.0` → `1.0.0`) — breaking changes

Check what is already on PyPI first — **PyPI permanently rejects re-uploading an
existing version**, so a mistake burns that version number:

```bash
pip index versions robotframework-mock
```

### 2. Verify the build locally

Tests are **not** a precondition of the publish workflow, so verify before
tagging:

```bash
pytest                                    # unit tests
robot test/keyword                        # keyword tests
pylint $(git ls-files '*.py')             # lint
```

Confirm the distribution builds and contains all three packages:

```bash
rm -rf build/ dist/ src/*.egg-info/
python -m build
python -m twine check dist/*
tar -tzf dist/*.tar.gz | grep -E "Mock(Library|Resource|Coverage)/"
```

### 3. Commit, tag and push

```bash
git add setup.cfg
git commit -m "Bump version to 0.4.0"
git push

git tag -a v0.4.0 -m "Release 0.4.0"
git push origin v0.4.0      # this triggers the release
```

Watch the run under the repository's Actions tab.

### 4. Verify the release

```bash
pip install --upgrade robotframework-mock
python -c "import MockLibrary, MockResource, MockCoverage; print('ok')"
```

## Testing a release first (optional)

To rehearse without consuming a real version number, upload to TestPyPI
manually:

```bash
python -m build
python -m twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ \
            robotframework-mock
```

The `--extra-index-url` is required so dependencies (`robotframework`) resolve
from real PyPI.

## Manual release (fallback)

If the workflow is unavailable:

```bash
rm -rf build/ dist/ src/*.egg-info/
python -m build
python -m twine check dist/*
python -m twine upload dist/*     # username: __token__, password: your API token
```

## Using the released package

```robot
*** Settings ***
Library    DatabaseLibrary
Library    MockLibrary    DatabaseLibrary    AS    MockDB
```

Coverage measurement is enabled as a listener rather than imported:

```bash
robot --listener MockCoverage:config=mock-coverage.toml tests/
```

See [README.md](README.md) for full usage of `MockLibrary`, `MockResource` and
`MockCoverage`.

## Troubleshooting

### `File already exists` on upload

That version is already on PyPI and cannot be overwritten. Bump the version in
`setup.cfg`, commit, and tag again.

### Tag pushed but nothing published

The workflow only matches tags beginning with `v` (e.g. `v0.4.0`, not `0.4.0`).
Check the Actions tab, and confirm `PYPI_API_TOKEN` is set.

### Import error after installing

Verify the install and that all packages shipped:

```bash
pip show -f robotframework-mock
```

### Clean build

```bash
rm -rf build/ dist/ src/*.egg-info/
python -m build
```
