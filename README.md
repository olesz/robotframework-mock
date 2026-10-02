# robotframework-mock

A Robot Framework library for mocking keywords in unit tests.

## Installation

### From PyPI (once published)

```bash
pip install robotframework-mock
```

### From source

```bash
git clone https://github.com/yourusername/robotframework-mock.git
cd robotframework-mock
pip install .
```

### For development

```bash
pip install -e .
pip install -r requirements-dev.txt
```

## Features

- Mock keywords from any Robot Framework library
- Mock keywords from Robot Framework resource files
- Mock Robot Framework's BuiltIn keywords
- Support for keywords with custom names via @keyword decorator
- Verify keyword calls and call counts
- Measure resource-file keyword coverage with configurable thresholds
- Simple API with three main keywords

## Usage

### Mock Library Keywords

Import the library you want to mock, then create a MockLibrary instance for it:

```robot
*** Settings ***
Library    DatabaseLibrary
Library    MockLibrary    DatabaseLibrary    WITH NAME    MockDB

*** Test Cases ***
Test With Mocked Keyword
    MockDB.Mock Keyword    query    return_value=test_data
    ${result}=    DatabaseLibrary.Query    SELECT * FROM users
    Should Be Equal    ${result}    test_data
    MockDB.Reset Mocks
```

### Verify Calls

Verify that a keyword was called and optionally check the call count:

```robot
*** Test Cases ***
Test Keyword Was Called
    MockDB.Mock Keyword    execute_sql    return_value=${None}
    Process User Registration
    MockDB.Verify Keyword Called    execute_sql    times=1
    MockDB.Reset Mocks
```

### Mock BuiltIn Keywords

Mock Robot Framework's built-in keywords using the same MockLibrary with "BuiltIn" as the library name:

```robot
*** Settings ***
Library    MockLibrary    BuiltIn    WITH NAME    MockBin

*** Test Cases ***
Test BuiltIn Mock
    MockBin.Mock Keyword    Convert To Binary    return_value=test_data
    ${result}=    Convert To Binary    aaa
    Should Be Equal    ${result}    test_data
    MockBin.Reset Mocks
```

### Mock Multiple Libraries

You can mock multiple libraries in the same test:

```robot
*** Settings ***
Library    DatabaseLibrary
Library    RequestsLibrary
Library    MockLibrary    DatabaseLibrary    WITH NAME    MockDB
Library    MockLibrary    RequestsLibrary    WITH NAME    MockReq

*** Test Cases ***
Test Multiple Mocks
    MockDB.Mock Keyword    query    return_value=user_data
    MockReq.Mock Keyword    get    return_value=api_response
    # Your test code here
    MockDB.Reset Mocks
    MockReq.Reset Mocks
```

### Mock Resource Keywords

Mock keywords from Robot Framework resource files:

```robot
*** Settings ***
Resource    my_resource.robot
Library     MockResource    my_resource.robot    WITH NAME    MockRes

*** Test Cases ***
Test Resource Keyword Mock
    MockRes.Mock Keyword    My Custom Keyword    return_value=mocked_value
    ${result}=    My Custom Keyword
    Should Be Equal    ${result}    mocked_value
    MockRes.Reset Mocks
```

## Keyword Coverage Measurement

`MockCoverage` measures how many of the keywords **defined** in your resource
files were actually **executed** by your tests — the Robot Framework analogue of
JaCoCo or coverage.py. Coverage requirements live in a TOML config file, and the
run fails if coverage falls below the configured threshold, so it can gate a CI
build.

Resource files are found by **recursively scanning directories** you list, so a
newly added resource file is measured automatically and cannot silently escape
the gate.

### Coverage model

Coverage uses the same aggregate model as standard coverage tools: a keyword
counts as covered if it is executed **at any point during the run**, regardless
of which test triggered it. This includes keywords reached indirectly through
other keywords.

A discovered resource file whose keywords are never executed reports
**0% coverage** by design.

Keyword names are read from the resource files themselves; the config only
selects *which files* participate.

### Configuration

Create a config file (e.g. `mock-coverage.toml`):

```toml
[coverage]
# Global minimum coverage percentage across all discovered resources
fail_under = 80.0

# Directories scanned recursively for resource files
paths = [
    "tests/core-common/resources",
    "tests/core-ui/resources",
]

# Which files to collect within those paths (default: ["*.resource"])
patterns = ["*.resource"]

# Optional exclusions, matched against the reported (relative) path
exclude = ["*deprecated*", "*/experimental/*"]

# Optional: stricter threshold for an individual file
[coverage.resources."tests/core-common/resources/vertica.resource"]
fail_under = 95.0
```

| Key | Default | Description |
|---|---|---|
| `fail_under` | `0.0` | Minimum overall coverage percentage |
| `paths` | *(none)* | Directories scanned recursively |
| `patterns` | `["*.resource"]` | Filename patterns to collect |
| `exclude` | `[]` | Patterns to skip |
| `[coverage.resources."<file>"]` | — | Per-file threshold override |

Both the global total and each individual resource must meet its threshold for
the run to pass.

All paths are resolved **relative to the config file's own directory**, so the
same config works no matter which directory you invoke `robot` from. Absolute
paths are used as-is. A file listed explicitly under `[coverage.resources]` is
always measured, even if it lies outside `paths`.

### Running

Enable it as a listener:

```bash
robot --listener MockCoverage:config=mock-coverage.toml tests/
```

Listener options are `name=value` pairs separated by colons:

| Option | Default | Description |
|---|---|---|
| `config` | `mock-coverage.toml` | Path to the TOML configuration file |
| `output` | `coverage.json` | JSON report path (directories are created) |
| `enforce` | `true` | Whether to fail the run when below threshold |
| `console` | `failing` | `failing` lists only breaches; `all` lists every resource |

```bash
# Full table, reporting only (no build failure)
robot --listener MockCoverage:config=cov.toml:output=build/coverage.json:enforce=false:console=all tests/
```

### Output

By default the console report lists only the resources that are below their
threshold, which keeps output readable across large resource trees:

```
Resource Keyword Coverage
  Resources below threshold (1):
  res/brand-new.resource  0/2    0.00%  FAIL (>=50.0)
  TOTAL                   3/8   37.50%  FAIL (>=50.0) [4 resources]
```

With `console=all`, every measured resource is listed:

```
Resource Keyword Coverage
  res/deep/nested/util.resource  1/2   50.00%  PASS (>=50.0)
  res/x/common.resource          1/2   50.00%  PASS (>=50.0)
  res/y/common.resource          1/2   50.00%  PASS (>=50.0)
  TOTAL                          3/6   50.00%  PASS (>=50.0) [3 resources]
```

When coverage is below threshold and `enforce` is enabled, the process exits with
a non-zero status **even if all tests passed**, failing the build.

A machine-readable JSON report is always written with the full per-file detail,
naming exactly which keywords were covered and which were missed:

```json
{
  "total": {
    "resources": 1,
    "defined": 4,
    "covered": 3,
    "percent": 75.0,
    "fail_under": 75.0,
    "passed": true
  },
  "resources": [
    {
      "path": "resources/coverage-demo.resource",
      "defined": 4,
      "covered": 3,
      "percent": 75.0,
      "fail_under": 75.0,
      "passed": true,
      "covered_keywords": ["Covered Keyword One", "Covered Keyword Three", "Covered Keyword Two"],
      "missed_keywords": ["Uncovered Keyword"]
    }
  ]
}
```

### Notes and limitations

- Executed keywords are attributed to their **real source file**, resolved
  through Robot Framework's namespace at call time. Resource files sharing the
  same base name in different directories are measured independently.
- Coverage is measured at **keyword granularity** (was this keyword executed?),
  not at line or branch level.
- Python library keywords are not measured — use `pytest` with `coverage.py` for
  those.
- TOML parsing uses the stdlib `tomllib` on Python 3.11+; on older versions the
  `tomli` backport is installed automatically as a dependency.

## Keywords

### Mock Keyword

Mock a keyword with a return value or side effect.

**Arguments:**
- `keyword_name` - Name of the keyword to mock
- `return_value` - Value to return when called (optional)
- `side_effect` - Callable to execute instead (optional)

**Example:**
```robot
MockDB.Mock Keyword    query    return_value=test_data
```

### Reset Mocks

Restore all mocked keywords to their original implementations.

**Example:**
```robot
MockDB.Reset Mocks
```

### Verify Keyword Called

Verify a keyword was called, optionally checking call count.

**Arguments:**
- `keyword_name` - Name of the keyword to verify
- `times` - Expected number of calls (optional)

**Example:**
```robot
MockDB.Verify Keyword Called    execute_sql    times=1
```

## How It Works

### MockLibrary

MockLibrary dynamically replaces keyword implementations:
1. Wraps the target library instance
2. Resolves keyword names to function names (handles @keyword decorator)
3. Stores original methods before mocking
4. Replaces methods with mock implementations using Python's unittest.mock.Mock
5. Returns mocked values or executes side effects
6. Tracks call counts for verification
7. Raises AttributeError if attempting to mock a non-existent keyword

### MockResource

MockResource patches Robot Framework's keyword execution:
1. Patches the Namespace.get_runner method
2. Intercepts keyword execution for the specified resource file
3. Replaces keyword body with Return statement containing mocked value
4. Tracks call counts for verification
5. Restores original keyword body on reset

### MockCoverage

MockCoverage measures resource keyword coverage as a listener:
1. Reads thresholds and scan paths from the TOML config file
2. Recursively discovers resource files under those paths
3. Parses each one with Robot Framework's own parsing API to enumerate the
   keywords it defines
4. Records executed keywords via the `start_keyword` listener event, resolving
   each keyword's real source file through Robot's namespace so same-named
   resources stay distinct
5. Computes per-resource and total coverage percentages at the end of the run
6. Writes a JSON report and prints a summary table
7. Exits non-zero if any threshold is unmet and enforcement is enabled

## Notes

- Both libraries use `ROBOT_LIBRARY_SCOPE = 'GLOBAL'` to maintain state across test cases
- Built on Python's unittest.mock.Mock for robust mocking capabilities
- MockLibrary supports any Robot Framework library, including BuiltIn
- MockResource works with resource files by patching the keyword execution pipeline

## License

See LICENSE file for details.