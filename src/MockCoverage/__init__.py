"""Resource-file keyword coverage measurement for Robot Framework.

``MockCoverage`` is a Robot Framework listener (API v3) that measures how many
of the keywords *defined* in your resource files were actually *executed*
during a test run, analogous to code-coverage tools such as JaCoCo or
coverage.py.

Resource files are discovered by **recursively scanning directories** listed in
a TOML config, so adding a new resource file automatically brings it under
measurement. Individual files may also be listed explicitly to give them a
stricter threshold.

The model is the standard aggregate one: a defined keyword counts as covered if
it is executed at any point during the run, regardless of which test triggered
it. Discovered resource files whose keywords are never executed get 0% coverage
by design.

Executed keywords are attributed to their **real source file path**, resolved
through Robot Framework's namespace at call time. Resource files sharing the
same base name in different directories are therefore measured independently.

Usage::

    robot --listener MockCoverage:config=mock-coverage.toml tests/

Optional listener arguments (``name=value`` pairs, colon-separated)::

    config=<path>     Path to the TOML config (default: mock-coverage.toml)
    output=<path>     Path to write the JSON report (default: coverage.json)
    enforce=<bool>    Fail the run on threshold breach (default: true)
    console=<mode>    Console detail: 'failing' (default) or 'all'

Example ``mock-coverage.toml``::

    [coverage]
    fail_under = 80.0
    paths = ["tests/core-common/resources", "tests/core-ui/resources"]
    patterns = ["*.resource"]
    exclude = ["*deprecated*"]

    [coverage.resources."tests/core-common/resources/vertica.resource"]
    fail_under = 95.0
"""
# pylint: disable=invalid-name
import fnmatch
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - exercised only on <3.11
    try:
        import tomli as tomllib  # Backport for Python 3.7-3.10
    except ModuleNotFoundError:
        tomllib = None

from robot.api import get_resource_model
from robot.api.parsing import ModelVisitor

from _mock_core import is_keyword_mocked


DEFAULT_CONFIG_PATH = "mock-coverage.toml"
DEFAULT_OUTPUT_PATH = "coverage.json"
DEFAULT_PATTERNS = ("*.resource",)


def normalize_path(path: str) -> str:
    """Return a canonical form of a path suitable for equality comparison.

    Uses pure string normalisation (no filesystem access) so that discovering
    thousands of resource files stays fast: ``..`` segments are collapsed and
    platform-appropriate case folding is applied.

    Symlinked paths are handled separately by a lazy fallback in the listener,
    because resolving symlinks requires expensive filesystem calls.

    Args:
        path: Any filesystem path.

    Returns:
        The canonical comparison key for that path.
    """
    return os.path.normcase(os.path.abspath(path))


def real_path_key(path: str) -> str:
    """Return a symlink-resolved comparison key for a path.

    This touches the filesystem and is therefore only used as a fallback when
    :func:`normalize_path` fails to match a resource.

    Args:
        path: Any filesystem path.

    Returns:
        The symlink-resolved comparison key.
    """
    return os.path.normcase(os.path.realpath(path))


def _basename_key(path: str) -> str:
    """Return the owner name Robot uses for a resource file.

    Robot Framework identifies resource keywords by the resource module name,
    which is the file's base name without its extension. This is used only as
    a cheap pre-filter; final attribution uses the resolved source path.
    """
    return os.path.splitext(os.path.basename(path))[0]


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
@dataclass
class CoverageConfig:
    """Parsed coverage configuration."""

    global_fail_under: float = 0.0
    paths: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=lambda: list(DEFAULT_PATTERNS))
    exclude: List[str] = field(default_factory=list)
    overrides: Dict[str, float] = field(default_factory=dict)
    base_dir: str = ""

    def resolve_path(self, path: str) -> str:
        """Resolve a configured path against the config file's directory.

        Relative paths are interpreted relative to the directory containing the
        config file, so a config works regardless of the directory ``robot`` is
        invoked from. Absolute paths are returned unchanged.

        Args:
            path: Path as written in the config file.

        Returns:
            The resolved path.
        """
        if os.path.isabs(path) or not self.base_dir:
            return path
        return os.path.join(self.base_dir, path)

    def display_path(self, abs_path: str) -> str:
        """Render an absolute path for reporting, relative to the config dir.

        Args:
            abs_path: Absolute filesystem path.

        Returns:
            A path relative to ``base_dir`` when possible, else ``abs_path``.
        """
        if not self.base_dir:
            return abs_path
        try:
            return os.path.relpath(abs_path, self.base_dir).replace(
                os.sep, "/"
            )
        except ValueError:
            # Different drive on Windows - no relative path exists.
            return abs_path


def _validate_threshold(value: float, name: str) -> None:
    if not 0.0 <= value <= 100.0:
        raise ValueError(f"{name} must be between 0 and 100, got {value}")


def parse_config(data: dict, base_dir: str = "") -> CoverageConfig:
    """Build a :class:`CoverageConfig` from a parsed TOML mapping.

    Args:
        data: Mapping as returned by ``tomllib.load`` / ``tomllib.loads``.
        base_dir: Directory that relative paths are resolved against, normally
            the directory containing the config file.

    Returns:
        A validated :class:`CoverageConfig`.

    Raises:
        ValueError: If a threshold is outside the 0-100 range, or if neither
            ``paths`` nor explicit resources are configured.
    """
    coverage = data.get("coverage", {}) or {}
    global_fail_under = float(coverage.get("fail_under", 0.0))
    _validate_threshold(global_fail_under, "coverage.fail_under")

    paths = list(coverage.get("paths", []) or [])
    patterns = list(coverage.get("patterns", []) or list(DEFAULT_PATTERNS))
    exclude = list(coverage.get("exclude", []) or [])

    overrides: Dict[str, float] = {}
    for path, settings in (coverage.get("resources", {}) or {}).items():
        settings = settings or {}
        fail_under = float(settings.get("fail_under", global_fail_under))
        _validate_threshold(
            fail_under, f'coverage.resources."{path}".fail_under'
        )
        overrides[path] = fail_under

    if not paths and not overrides:
        raise ValueError(
            "Coverage config defines nothing to measure. Add 'paths' with "
            "directories to scan recursively, e.g.\n"
            '  [coverage]\n  paths = ["tests/resources"]'
        )

    return CoverageConfig(
        global_fail_under=global_fail_under,
        paths=paths,
        patterns=patterns,
        exclude=exclude,
        overrides=overrides,
        base_dir=base_dir,
    )


def load_config(path: str) -> CoverageConfig:
    """Load and parse a TOML coverage config file.

    Args:
        path: Path to the TOML configuration file.

    Returns:
        A :class:`CoverageConfig`.

    Raises:
        RuntimeError: If TOML parsing is unavailable.
        FileNotFoundError: If the config file does not exist.
    """
    if tomllib is None:  # pragma: no cover
        raise RuntimeError(
            "TOML parsing is unavailable. Python 3.11+ provides 'tomllib'; "
            "on older versions install the backport with: pip install tomli"
        )
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"Coverage config not found: {abs_path}")
    with open(abs_path, "rb") as handle:
        data = tomllib.load(handle)
    return parse_config(data, base_dir=os.path.dirname(abs_path))


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
@dataclass
class ResourceTarget:
    """A resource file selected for coverage measurement."""

    display_path: str
    abs_path: str
    fail_under: float


def _is_excluded(display_path: str, exclude: List[str]) -> bool:
    return any(fnmatch.fnmatch(display_path, pat) for pat in exclude)


def discover_targets(config: CoverageConfig) -> List[ResourceTarget]:
    """Find every resource file the configuration selects for measurement.

    Each directory in ``config.paths`` is scanned recursively for files
    matching ``config.patterns``, minus anything matching ``config.exclude``.
    Files listed explicitly under ``[coverage.resources]`` are always included
    and take their declared threshold.

    Args:
        config: The parsed coverage configuration.

    Returns:
        Resource targets sorted by display path, de-duplicated by real path.

    Raises:
        FileNotFoundError: If a configured directory or explicit file is
            missing.
    """
    by_abs: Dict[str, ResourceTarget] = {}

    for raw_path in config.paths:
        root = config.resolve_path(raw_path)
        if not os.path.isdir(root):
            raise FileNotFoundError(
                f"Coverage path is not a directory: {os.path.abspath(root)}"
            )
        # os.walk is used instead of Path.rglob because it avoids a stat call
        # per entry, which dominates runtime on large or network filesystems.
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                if not any(
                    fnmatch.fnmatch(filename, pat)
                    for pat in config.patterns
                ):
                    continue
                abs_path = os.path.abspath(os.path.join(dirpath, filename))
                display = config.display_path(abs_path)
                if _is_excluded(display, config.exclude):
                    continue
                key = normalize_path(abs_path)
                if key not in by_abs:
                    by_abs[key] = ResourceTarget(
                        display_path=display,
                        abs_path=abs_path,
                        fail_under=config.global_fail_under,
                    )

    # Explicit entries win: they are always measured, with their own threshold.
    for raw_path, fail_under in config.overrides.items():
        resolved = config.resolve_path(raw_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(
                f"Resource file not found: {os.path.abspath(resolved)}"
            )
        abs_path = os.path.abspath(resolved)
        key = normalize_path(abs_path)
        by_abs[key] = ResourceTarget(
            display_path=config.display_path(abs_path),
            abs_path=abs_path,
            fail_under=fail_under,
        )

    return sorted(by_abs.values(), key=lambda t: t.display_path)


# --------------------------------------------------------------------------- #
# Keyword parsing
# --------------------------------------------------------------------------- #
class _KeywordNameCollector(ModelVisitor):
    """Collects defined keyword names from a parsed resource model."""

    def __init__(self):
        """Initialise with an empty name list."""
        self.names: List[str] = []

    def visit_KeywordName(self, node):
        """Collect the name of each keyword definition encountered."""
        self.names.append(node.name)


def parse_defined_keywords(resource_path: str) -> List[str]:
    """Return the list of keyword names defined in a resource file.

    Args:
        resource_path: Path to the ``.robot`` / ``.resource`` file.

    Returns:
        Keyword names exactly as declared in the file.

    Raises:
        FileNotFoundError: If the resource file does not exist.
    """
    abs_path = os.path.abspath(resource_path)
    if not os.path.isfile(abs_path):
        raise FileNotFoundError(f"Resource file not found: {abs_path}")
    collector = _KeywordNameCollector()
    collector.visit(get_resource_model(abs_path))
    return collector.names


# --------------------------------------------------------------------------- #
# Coverage computation
# --------------------------------------------------------------------------- #
@dataclass
class ResourceCoverage:
    """Coverage result for a single resource file."""

    path: str
    fail_under: float
    defined: List[str]
    covered: List[str]

    @property
    def total(self) -> int:
        """Number of keywords defined in the resource."""
        return len(self.defined)

    @property
    def hit(self) -> int:
        """Number of defined keywords that were executed."""
        return len(self.covered)

    @property
    def missed(self) -> List[str]:
        """Defined keywords that were never executed."""
        covered = set(self.covered)
        return [name for name in self.defined if name not in covered]

    @property
    def percent(self) -> float:
        """Coverage percentage for this resource."""
        if self.total == 0:
            # A resource with no keywords is vacuously fully covered.
            return 100.0
        return 100.0 * self.hit / self.total

    @property
    def passed(self) -> bool:
        """Whether this resource meets its configured threshold."""
        return self.percent >= self.fail_under


@dataclass
class CoverageReport:
    """Aggregate coverage result across all measured resources."""

    resources: List[ResourceCoverage]
    global_fail_under: float

    @property
    def total(self) -> int:
        """Total number of keywords defined across all resources."""
        return sum(r.total for r in self.resources)

    @property
    def hit(self) -> int:
        """Total number of covered keywords across all resources."""
        return sum(r.hit for r in self.resources)

    @property
    def percent(self) -> float:
        """Overall coverage percentage."""
        if self.total == 0:
            return 100.0
        return 100.0 * self.hit / self.total

    @property
    def failing(self) -> List[ResourceCoverage]:
        """Resources that do not meet their own threshold."""
        return [r for r in self.resources if not r.passed]

    @property
    def passed(self) -> bool:
        """Whether the global and every per-resource threshold is met."""
        global_ok = self.percent >= self.global_fail_under
        return global_ok and not self.failing

    def to_dict(self) -> dict:
        """Serialise the report into a JSON-friendly dict."""
        return {
            "total": {
                "resources": len(self.resources),
                "defined": self.total,
                "covered": self.hit,
                "percent": round(self.percent, 2),
                "fail_under": self.global_fail_under,
                "passed": self.passed,
            },
            "resources": [
                {
                    "path": r.path,
                    "defined": r.total,
                    "covered": r.hit,
                    "percent": round(r.percent, 2),
                    "fail_under": r.fail_under,
                    "passed": r.passed,
                    "covered_keywords": sorted(r.covered),
                    "missed_keywords": sorted(r.missed),
                }
                for r in self.resources
            ],
        }

    def format_summary(self, detail: str = "failing") -> str:
        """Return a human-readable coverage table.

        Args:
            detail: ``"all"`` lists every measured resource; ``"failing"``
                (default) lists only resources below their threshold, which
                keeps output readable across large resource trees.

        Returns:
            The formatted summary text.
        """
        shown = self.resources if detail == "all" else self.failing
        lines = ["Resource Keyword Coverage"]
        width = max(
            [len(r.path) for r in shown] + [len("TOTAL")]
        )
        if detail != "all" and shown:
            lines.append(f"  Resources below threshold ({len(shown)}):")
        for r in shown:
            status = "PASS" if r.passed else "FAIL"
            lines.append(
                f"  {r.path:<{width}}  {r.hit}/{r.total}  "
                f"{r.percent:6.2f}%  {status} (>={r.fail_under})"
            )
        if detail != "all" and not shown:
            lines.append(
                f"  All {len(self.resources)} resources meet their thresholds."
            )
        status = "PASS" if self.passed else "FAIL"
        lines.append(
            f"  {'TOTAL':<{width}}  {self.hit}/{self.total}  "
            f"{self.percent:6.2f}%  {status} (>={self.global_fail_under}) "
            f"[{len(self.resources)} resources]"
        )
        return "\n".join(lines)


def compute_coverage(
    targets: List[ResourceTarget],
    defined_by_path: Dict[str, List[str]],
    executed_by_path: Dict[str, Set[str]],
    global_fail_under: float = 0.0,
) -> CoverageReport:
    """Compute a coverage report from parsed definitions and execution data.

    Args:
        targets: Resource files being measured.
        defined_by_path: Normalized resource path -> defined keyword names.
        executed_by_path: Normalized resource path -> executed keyword names.
        global_fail_under: Overall minimum coverage percentage.

    Returns:
        A :class:`CoverageReport`.
    """
    results: List[ResourceCoverage] = []
    for target in targets:
        key = normalize_path(target.abs_path)
        defined = defined_by_path.get(key, [])
        executed = executed_by_path.get(key, set())
        covered = [name for name in defined if name in executed]
        results.append(
            ResourceCoverage(
                path=target.display_path,
                fail_under=target.fail_under,
                defined=defined,
                covered=covered,
            )
        )
    return CoverageReport(
        resources=results, global_fail_under=global_fail_under
    )


# --------------------------------------------------------------------------- #
# Execution tracking
# --------------------------------------------------------------------------- #
class ExecutionTracker:
    """Records which measured resource keywords actually execute.

    Executed keywords are attributed to their real source file, resolved
    through Robot Framework's namespace at call time, so resource files that
    share a base name are tracked independently.
    """

    def __init__(self, tracked_paths: Set[str]):
        """Initialise the tracker.

        Args:
            tracked_paths: Normalized paths of the resources being measured.
        """
        self._tracked = tracked_paths
        self._owner_names = {_basename_key(p) for p in tracked_paths}
        self._executed: Dict[str, Set[str]] = {}
        self._source_cache: Dict[tuple, Optional[str]] = {}
        self._real_index: Optional[Dict[str, str]] = None

    @property
    def executed(self) -> Dict[str, Set[str]]:
        """Mapping of resource path -> executed keyword names."""
        return self._executed

    def reset_cache(self) -> None:
        """Drop the source-resolution cache.

        Called between suites because keyword names resolve per namespace.
        """
        self._source_cache.clear()

    def record(self, owner: Optional[str], name: str) -> None:
        """Record a keyword execution if it belongs to a measured resource.

        Keywords whose body is currently replaced by a ``MockResource`` mock are
        ignored: the real body never ran, so counting them would credit the
        resource with coverage it did not earn.

        Args:
            owner: Robot's owner name for the keyword (resource base name).
            name: The executed keyword's name.
        """
        # Cheap pre-filter before the more costly source resolution.
        if owner not in self._owner_names:
            return
        source = self._resolve_source(owner, name)
        if source and not is_keyword_mocked(source, name):
            self._executed.setdefault(source, set()).add(name)

    def _resolve_source(self, owner: str, name: str) -> Optional[str]:
        """Resolve and cache the source file of an executing keyword."""
        cache_key = (owner, name)
        if cache_key in self._source_cache:
            return self._source_cache[cache_key]
        source = None
        try:
            # Imported lazily: only meaningful during execution.
            # pylint: disable-next=import-outside-toplevel
            from robot.running.context import EXECUTION_CONTEXTS

            context = EXECUTION_CONTEXTS.current
            if context is not None:
                runner = context.namespace.get_runner(name, False)
                raw = getattr(getattr(runner, "keyword", None), "source", None)
                if raw:
                    source = self._match_source(str(raw))
        except Exception:  # pylint: disable=broad-except
            # Coverage measurement must never break a test run.
            source = None
        self._source_cache[cache_key] = source
        return source

    def _match_source(self, raw_source: str) -> Optional[str]:
        """Map a Robot-reported source path onto a measured resource key.

        Tries fast string normalisation first and only falls back to symlink
        resolution if that misses, so symlinked resource trees still work
        without slowing down the common case.

        Args:
            raw_source: Source path as reported by Robot Framework.

        Returns:
            The matching tracked key, or ``None`` if the file is not measured.
        """
        key = normalize_path(raw_source)
        if key in self._tracked:
            return key
        if self._real_index is None:
            self._real_index = {
                real_path_key(path): path for path in self._tracked
            }
        return self._real_index.get(real_path_key(raw_source))


# --------------------------------------------------------------------------- #
# Listener
# --------------------------------------------------------------------------- #
@dataclass
class _ReportOptions:
    """Output and gating options for the listener."""

    output_path: str
    enforce: bool
    console: str


class MockCoverage:
    """Robot Framework listener measuring resource keyword coverage.

    See the module docstring for configuration and usage details.
    """

    ROBOT_LISTENER_API_VERSION = 3

    def __init__(
        self,
        config: str = DEFAULT_CONFIG_PATH,
        output: str = DEFAULT_OUTPUT_PATH,
        enforce: str = "true",
        console: str = "failing",
    ):
        """Initialise the listener.

        Args:
            config: Path to the TOML coverage config.
            output: Path for the JSON report written on close.
            enforce: ``"true"``/``"false"`` - whether to fail the run when
                coverage is below threshold.
            console: ``"failing"`` or ``"all"`` - console report detail.
        """
        self._options = _ReportOptions(
            output_path=output,
            enforce=str(enforce).strip().lower() in ("true", "1", "yes"),
            console=str(console).strip().lower(),
        )

        cfg = load_config(config)
        self._global_fail_under = cfg.global_fail_under
        self._targets = discover_targets(cfg)
        self._defined_by_path: Dict[str, List[str]] = {
            normalize_path(t.abs_path): parse_defined_keywords(t.abs_path)
            for t in self._targets
        }
        self._tracker = ExecutionTracker(set(self._defined_by_path))
        self._report: Optional[CoverageReport] = None

    @property
    def report(self) -> Optional[CoverageReport]:
        """The computed report, available after the run closes."""
        return self._report

    # -- listener hooks ---------------------------------------------------- #
    def start_suite(self, data, result):
        """Reset per-suite keyword resolution state.

        Args:
            data: Robot Framework suite data (unused).
            result: Robot Framework suite result (unused).
        """
        # pylint: disable=unused-argument
        self._tracker.reset_cache()

    def start_keyword(self, data, result):
        """Record execution of a keyword belonging to a measured resource.

        Args:
            data: Robot Framework keyword data (unused).
            result: Keyword result carrying ``owner`` and ``name``.
        """
        # pylint: disable=unused-argument
        self._tracker.record(getattr(result, "owner", None), result.name)

    def close(self):
        """Compute coverage, write the report, and gate the run."""
        self._report = compute_coverage(
            self._targets,
            self._defined_by_path,
            self._tracker.executed,
            self._global_fail_under,
        )
        self._write_report(self._report)
        print(
            "\n" + self._report.format_summary(self._options.console),
            file=sys.stderr,
        )
        if self._options.enforce and not self._report.passed:
            print(
                "\nERROR: Resource keyword coverage below required threshold.",
                file=sys.stderr,
            )
            sys.exit(1)

    def _write_report(self, report: CoverageReport) -> None:
        abs_path = os.path.abspath(self._options.output_path)
        parent = os.path.dirname(abs_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as handle:
            json.dump(report.to_dict(), handle, indent=2)
