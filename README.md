# robotframework-mock

A Robot Framework library for mocking keywords in unit tests.

## Installation

### Requirements

- Python 3.10 – 3.14
- Robot Framework 7.0 – 7.5

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
- Inspect and verify the arguments a mocked keyword was called with
- Inspect the order in which mocked keywords were called
- Inspect that order across several mock instances at once
- Capture the messages a keyword logged, and assert on their level
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

`return_value` may be any Python object, not only a string, so a keyword that
forwards a query result or a parsed response body can be mocked directly:

```robot
${rows}=    Evaluate    [['Europe/Budapest']]
MockRes.Mock Keyword    Run Query    return_value=${rows}
```

A `side_effect` that is an exception makes the mocked keyword **fail**, which is
how a test drives the error branch of a keyword that guards its dependency. The
failure is a normal Robot failure, so `Run Keyword And Ignore Error`, `Run Keyword
And Return Status` and `TRY`/`EXCEPT` all catch it:

```robot
MockRes.Mock Keyword    Run Query    side_effect=${{ RuntimeError('db unavailable') }}

${status}    ${message}=    Run Keyword And Ignore Error    Run Query    SELECT 1
Should Be Equal    ${status}     FAIL
Should Be Equal    ${message}    db unavailable
```

A failing call is still recorded, so `Get Keyword Call Args`, `Verify Keyword
Called` and `Get Keyword Call Order` include it.

### Keywords with a custom name

`MockLibrary` finds a library keyword by the name a test author actually writes,
including when `@keyword` gives it a name that does not follow from the method
name:

```python
class DnsCacheManager:
    @keyword('Is DNS Entry Resolvable')
    def is_dns_cache_entry_resolvable(self, domain_name):
        ...
```

```robot
MockDns.Mock Keyword    Is DNS Entry Resolvable    return_value=10.0.0.1
${args}=    MockDns.Get Keyword Call Args    Is DNS Entry Resolvable
```

Mocking and inspecting both use the keyword name; the underlying method name is
never needed.

### Branches that are not taken

Robot runs the body of **every** `IF`/`ELSE` branch and marks the ones not taken
as NOT RUN. A mocked keyword in a skipped branch is not recorded as called, so a
test can assert which branch a keyword chose:

```robot
MockRes.Mock Keyword    Read From Postgres    return_value=${rows}
MockRes.Mock Keyword    Read From Geode       return_value=${rows}

Fetch Data

MockRes.Verify Keyword Called    Read From Geode    times=0
```

This holds for the call count, the recorded arguments and the call order alike.

### Mocked keyword setup and teardown

`MockResource` replaces only a keyword's **body**. Its `[Setup]` and `[Teardown]`
still run, which keeps them observable — a test can assert that a teardown
released a lock, for instance.

That is a problem when the teardown cleans up state the replaced body would have
created, because it then fails on the mocked call. Suppress it per mock:

```robot
# Init Client acquires a lock in its body and releases it in its teardown.
# Without the body there is no lock to release, so skip the teardown.
MockRes.Mock Keyword    Init Client    return_value=alias    skip_teardown=${True}
MockRes.Mock Keyword    Init Client    return_value=alias    skip_setup=${True}
```

Both default to `False`, so existing tests are unaffected. `Reset Mocks`
restores a suppressed setup or teardown along with the body, and so does
re-mocking the keyword without the flag — see
[Re-mocking the same keyword](#re-mocking-the-same-keyword).

Prefer the default when the setup or teardown is part of the contract you are
testing, and skip it when it is an implementation detail of a keyword the test
is only standing in for.

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

### Verify Keyword Called With

Verify a keyword was called with the given arguments. Passes when **at least one**
recorded call matches, so the order of calls does not matter.

**Arguments:**
- `keyword_name` - Name of the keyword to verify
- `*args` - Expected positional arguments
- `**kwargs` - Expected named arguments

**Example:**
```robot
MockDB.Verify Keyword Called With    execute_sql    SELECT 1    timeout=${30}
```

Arguments are compared with Python equality, so types matter. Values are
recorded exactly as Robot Framework passed them to the keyword: test data is
string data, but Robot converts arguments of keywords that declare argument
types, and which built-in keywords declare types differs between Robot
Framework versions. When a recorded value is therefore not a string, give the
expectation as a typed Robot variable (`timeout=${30}` rather than
`timeout=30`), or read the call back with `Get Keyword Call Kwargs` and assert
on it with a type-insensitive comparison.

### Get Keyword Call Args

Return the positional arguments of one call to a mocked keyword.

**Arguments:**
- `keyword_name` - Name of the mocked keyword
- `index` - Zero-based call index, negative counts from the end (default `0`)

**Example:**
```robot
${args}=    MockDB.Get Keyword Call Args    execute_sql    index=0
Should Be Equal    ${args}[0]    SELECT 1
```

### Get Keyword Call Kwargs

Return the named arguments of one call to a mocked keyword.

**Arguments:**
- `keyword_name` - Name of the mocked keyword
- `index` - Zero-based call index, negative counts from the end (default `0`)

**Example:**
```robot
${kwargs}=    MockDB.Get Keyword Call Kwargs    execute_sql
Should Be Equal    ${kwargs}[timeout]    ${30}
```

### Get Keyword Call Count

Return how many times a mocked keyword was called.

**Example:**
```robot
${count}=    MockDB.Get Keyword Call Count    execute_sql
```

### Get Keyword Call Order

Return the mocked keywords in the order they were called, as a list of names.

Covers keywords mocked through the same library instance. This is what
establishes ordering *between* different mocks — an individual mock's call
history cannot show how it interleaved with its siblings.

A keyword called more than once appears once per call. Keywords that were mocked
but never called do not appear, and calls made on a keyword's return value are
not included.

**Example:**
```robot
MockRes.Mock Keyword    Init Client    return_value=alias
MockRes.Mock Keyword    Run Query      return_value=${rows}

Fetch Data

${order}=    MockRes.Get Keyword Call Order
Should Be Equal    ${order}    ${{ ['Init Client', 'Run Query'] }}
```

For ordering across *several* mock instances, see
[Get Global Call Order](#get-global-call-order).

### Get Global Call Order

Return the mocked keywords from **every** mock instance in the order they were
called, as a list of names. Provided by the `MockCallOrder` library, which has
to be imported separately:

```robot
Library    MockCallOrder
```

`Get Keyword Call Order` is limited to one library instance. This keyword is for
the case that one cannot cover: the contract is the *interleaving* of calls made
through different instances — "raise the alarm, restart the service, then wait
for the alarm to clear", where the alarm and the restart are mocked on two
different resources.

It is a separate library because the timeline belongs to no single mock. Keeping
it on the instances would make every instance expose the same keyword, so a suite
with two mocks — the only situation where a cross-instance order is interesting —
would have to pick one instance to ask, which reads as if the answer were that
instance's.

A keyword called more than once appears once per call, and a call that raised is
still a call, so retry sequences are visible. Keywords mocked but never called do
not appear.

The order is **not** cleared by `Reset Mocks`: resetting one instance must not
discard another instance's history. Clear it explicitly with
`Reset Global Call Order`, normally from the test setup.

**Example:**
```robot
Library    MockResource     alarm.resource    AS    MockAlarm
Library    MockResource     service.resource    AS    MockService
Library    MockCallOrder

Reset Global Call Order
MockAlarm.Mock Keyword      Wait For Alarm      return_value=${None}
MockService.Mock Keyword    Scale Deployment    return_value=${None}

Restart With Alarm Check

${order}=    Get Global Call Order
Should Be Equal    ${order}    ${{ ['Wait For Alarm', 'Scale Deployment', 'Wait For Alarm'] }}
```

Pass `qualified=${True}` to prefix each name with the library or resource it was
mocked on, which tells two identically named keywords apart:

```robot
${order}=    Get Global Call Order    qualified=${True}
Should Be Equal    ${order}[0]    alarm.resource.Wait For Alarm
```

This replaces wiring a `side_effect` that appends to a shared list, which was
previously the only way to observe cross-instance ordering — and which cannot be
combined with a `side_effect` the test needs for its own purposes.

### Reset Global Call Order

Forget the call order recorded across all mock instances. Call it before the
mocks whose order a test asserts are installed, so one test cannot see another
test's calls.

## Capturing Log Messages

A keyword's log output is part of its contract. A wrapper that takes a `${level}`
argument and drops it looks identical from the outside — the message still
appears, only at the wrong level — so a test that cannot read the log cannot
tell the two apart. Robot writes messages to `log.html`, which is not available
while the test runs, so the only way to see them is to listen for them.

The `LogCapture` library does that, and has to be imported separately:

```robot
Library    LogCapture
```

**It raises the log level while capturing and puts it back afterwards.** Robot
filters messages below the active log level *before* offering them to a listener,
so at the default `INFO` a `DEBUG` message never arrives — measured: a
listener at `INFO` sees `['INFO', 'WARN']` out of a DEBUG/INFO/WARN sequence.
Leaving that to the caller makes "nothing was logged" and "the message was
filtered out" indistinguishable, which is the very confusion the test is written
to resolve.

Capturing ends with the test that started it: the level is put back and the
recording let go, so neither leaks into the next test. Robot also logs a test's
own failure as a message, which is part of why the recording is dropped.

### Start Capturing Log Messages

Forget earlier messages and start recording, raising the log level to `level`
(default `DEBUG`). Pass `level=NONE` to leave the level untouched — for a
test asserting what a *given* log level does and does not write.

### Get Captured Log Messages

Return the captured messages, oldest first. Each is a dictionary with `level`,
`message`, `timestamp` and `html`, so a test can read `${messages}[0][level]`.

Optional `level` and `pattern` arguments filter the result: `level` matches
exactly and case-insensitively, `pattern` is a case-sensitive glob, so a partial
match needs its own wildcards.

**Example:**
```robot
Library    LogCapture

Start Capturing Log Messages
Rotate Credentials
${warnings}=    Get Captured Log Messages    level=WARN
Length Should Be    ${warnings}    1
Should Be Equal     ${warnings}[0][message]    credentials rotated
```

### Captured Log Should Contain

Fail unless a captured message matches the given glob, optionally requiring a
`level` and an exact `count` of matches. The failure lists every captured
message, because "the log line is missing" and "the log line is there at another
level" need telling apart and a bare assertion error cannot do that.

**Example:**
```robot
Start Capturing Log Messages
Refresh Data
Captured Log Should Contain    *retrying*    level=WARN    count=3
```

### Stop Capturing Log Messages

Stop recording, put the log level back, and return what was captured. Needed only
when a test logs something afterwards that it does not want recorded; otherwise
capturing ends with the test.

**Example:**
```robot
*** Settings ***
Library    MockCallOrder
Test Setup    Reset Global Call Order
```

## How It Works

### MockLibrary

MockLibrary dynamically replaces keyword implementations:
1. Wraps the target library instance
2. Resolves keyword names to function names (handles @keyword decorator)
3. Stores original methods before mocking
4. Replaces methods with mock implementations using Python's unittest.mock.Mock
5. Returns mocked values or executes side effects
6. Tracks call counts and call arguments for verification
7. Raises AttributeError if attempting to mock a non-existent keyword

#### Mocks are installed on the library class

Step 4 replaces the method on the target library's **class**, not on the
instance. Two consequences are worth knowing, because neither is reported as an
error:

**A mock stays active until `Reset Mocks`, across tests and suites.** The mock
is not scoped to the test that created it. A test that mocks a keyword and
leaves without resetting hands the mock to everything that follows. Reset in a
teardown rather than at the end of a test body, so the mock is also removed when
the test fails midway.

**Two `MockLibrary` instances wrapping the same library share one mock.** Last
registration wins, and resetting *either* instance restores the real method:

```robot
Library    MockLibrary    DateTime    WITH NAME    MockA
Library    MockLibrary    DateTime    WITH NAME    MockB
...
MockA.Mock Keyword    Convert Time    return_value=from-a
MockB.Mock Keyword    Convert Time    return_value=from-b
${result}=    Convert Time    12:00:00      # from-b: MockA's mock was overwritten
MockB.Reset Mocks
${result}=    Convert Time    12:00:00      # the real keyword, although MockA never reset
```

Use a single alias per library, and separate aliases only for *different*
libraries. `MockResource` is not affected: it keys mocks per resource file, so
instances for different resources are independent.

### MockResource

MockResource patches Robot Framework's keyword execution:
1. Patches the Namespace.get_runner method
2. Intercepts keyword execution for the specified resource file
3. Resolves the call's arguments - variables are replaced, and a `name=value`
   argument becomes a named argument when the keyword declares that name - so
   mocks record what the keyword was really called with
4. Replaces keyword body with Return statement containing mocked value
5. Tracks call counts and call arguments for verification
6. Restores original keyword body on reset

#### Re-mocking the same keyword

Mocking a keyword that is already mocked **replaces the mock and keeps the saved
original**, so `Reset Mocks` still restores the real keyword. The new mock starts
with an empty call history, so a call recorded before it was replaced is no
longer visible to `Verify Keyword Called`, `Get Keyword Call Args` and the rest.

The original is saved on the first mock only, and that matters more here than in
`MockLibrary`. Step 4 replaces the body lazily, on the first *call*, so a second
mock that saved the body again would save the injected RETURN as "the original" —
and `Reset Mocks` would then install that mock permanently. Resource keyword
objects are shared for the whole run, so every later test and suite would get it
too, failing with `Variable '${__mock_resource_return__}' not found`.

The name is normalized before it is used as a key, so `Fetch Rows` and
`fetch_rows` are the same keyword rather than two entries with two "originals".

`skip_setup` and `skip_teardown` apply exactly as given on *every* call, so
re-mocking without them puts a previously suppressed setup or teardown back:

```robot
MockRes.Mock Keyword    Init Client    return_value=alias    skip_teardown=${True}
MockRes.Mock Keyword    Init Client    return_value=other    # the teardown runs again
```

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
- `LogCapture` is a library and its own listener, which is how it sees log messages
- Built on Python's unittest.mock.Mock for robust mocking capabilities
- MockLibrary supports any Robot Framework library, including BuiltIn
- MockResource works with resource files by patching the keyword execution pipeline

## License

See LICENSE file for details.