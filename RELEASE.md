# Release Guide

## Prerequisites

1. Install build tools:
```bash
pip install build twine
```

2. Create accounts on:
   - [PyPI](https://pypi.org/account/register/) (production)
   - [TestPyPI](https://test.pypi.org/account/register/) (testing)

## Release Steps

### 1. Update Version

Update version in:
- `setup.py` (line 8)
- `src/mock/__init__.py` (line 3)

### 2. Build the Package

```bash
python -m build
```

This creates:
- `dist/robotframework-mock-X.Y.Z.tar.gz` (source distribution)
- `dist/robotframework_mock-X.Y.Z-py3-none-any.whl` (wheel)

### 3. Test on TestPyPI (Optional but Recommended)

Upload to TestPyPI:
```bash
python -m twine upload --repository testpypi dist/*
```

Test installation:
```bash
pip install --index-url https://test.pypi.org/simple/ robotframework-mock
```

### 4. Upload to PyPI

```bash
python -m twine upload dist/*
```

Enter your PyPI credentials when prompted.

### 5. Verify Installation

```bash
pip install robotframework-mock
```

### 6. Tag the Release

```bash
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Using in Robot Framework

After installation, import as:

```robot
*** Settings ***
Library    MockLibrary    DatabaseLibrary    WITH NAME    MockDB
```

## Local Development Installation

For local testing before release:

```bash
pip install -e .
```

This installs in "editable" mode, allowing you to test changes without reinstalling.

## Troubleshooting

### Import Error in Robot Framework

If you get import errors, verify the package is installed:
```bash
pip show robotframework-mock
```

### Clean Build

To clean previous builds:
```bash
rm -rf build/ dist/ *.egg-info/
```

Then rebuild with `python -m build`.
