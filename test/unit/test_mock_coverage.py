"""Unit tests for MockCoverage coverage measurement."""
# pylint: disable=protected-access
import json
import os

import pytest

from MockCoverage import (
    CoverageConfig,
    ResourceTarget,
    compute_coverage,
    discover_targets,
    load_config,
    normalize_path,
    parse_config,
    parse_defined_keywords,
    real_path_key,
    _basename_key,
)

RESOURCES_DIR = os.path.join(
    os.path.dirname(__file__), "..", "keyword", "resources"
)
RESOURCE_1 = os.path.join(RESOURCES_DIR, "resource-test.resource")


def _write(path, text):
    """Write text to path, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _resource(*names):
    """Return resource-file content defining the given keyword names."""
    body = "".join(f"{name}\n    RETURN    x\n" for name in names)
    return f"*** Keywords ***\n{body}"


# --------------------------------------------------------------------------- #
# Config parsing
# --------------------------------------------------------------------------- #
def test_parse_config_with_paths():
    """Test parsing a config that scans directories."""
    cfg = parse_config(
        {"coverage": {"fail_under": 80.0, "paths": ["res"]}}
    )
    assert cfg.global_fail_under == 80.0
    assert cfg.paths == ["res"]
    assert cfg.patterns == ["*.resource"]


def test_parse_config_custom_patterns_and_exclude():
    """Test custom include patterns and exclusions are parsed."""
    cfg = parse_config(
        {
            "coverage": {
                "paths": ["res"],
                "patterns": ["*.resource", "*.robot"],
                "exclude": ["*deprecated*"],
            }
        }
    )
    assert cfg.patterns == ["*.resource", "*.robot"]
    assert cfg.exclude == ["*deprecated*"]


def test_parse_config_per_resource_override():
    """Test explicit per-resource thresholds are captured."""
    cfg = parse_config(
        {
            "coverage": {
                "fail_under": 80.0,
                "paths": ["res"],
                "resources": {"res/a.resource": {"fail_under": 100.0}},
            }
        }
    )
    assert cfg.overrides == {"res/a.resource": 100.0}


def test_parse_config_requires_something_to_measure():
    """Test a config with neither paths nor resources is rejected."""
    with pytest.raises(ValueError, match="nothing to measure"):
        parse_config({"coverage": {"fail_under": 80.0}})


@pytest.mark.parametrize("bad", [-1.0, 100.1, 150.0])
def test_parse_config_rejects_out_of_range_threshold(bad):
    """Test thresholds outside 0-100 are rejected."""
    with pytest.raises(ValueError, match="between 0 and 100"):
        parse_config({"coverage": {"fail_under": bad, "paths": ["res"]}})


def test_basename_key():
    """Test the owner key is the file base name without extension."""
    assert _basename_key("a/b/my.resource") == "my"
    assert _basename_key("my.robot") == "my"


def test_load_config_sets_base_dir(tmp_path):
    """Test load_config resolves paths relative to the config file."""
    cfg_dir = tmp_path / "cfg"
    cfg_dir.mkdir()
    cfg_file = cfg_dir / "cov.toml"
    cfg_file.write_text('[coverage]\npaths = ["res"]\n')
    cfg = load_config(str(cfg_file))
    assert cfg.base_dir == str(cfg_dir)
    assert cfg.resolve_path("res") == str(cfg_dir / "res")


def test_load_config_missing_file():
    """Test loading a non-existent config raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("no-such-config.toml")


def test_resolve_path_leaves_absolute_untouched():
    """Test absolute configured paths are used as-is."""
    cfg = CoverageConfig(base_dir="/project/cfg")
    assert cfg.resolve_path("/elsewhere/a.resource") == "/elsewhere/a.resource"


# --------------------------------------------------------------------------- #
# Path normalization
# --------------------------------------------------------------------------- #
def test_normalize_path_collapses_parent_segments():
    """Test normalization removes '..' segments without touching the disk."""
    assert normalize_path("/a/b/../c.resource") == os.path.normcase(
        os.path.abspath("/a/c.resource")
    )


def test_normalize_path_is_idempotent():
    """Test normalizing an already-normalized path is stable."""
    once = normalize_path("/a/b/c.resource")
    assert normalize_path(once) == once


def test_real_path_key_resolves_symlinks(tmp_path):
    """Test the fallback key resolves symlinks to the real file."""
    target = tmp_path / "real.resource"
    target.write_text(_resource("A"))
    link = tmp_path / "link.resource"
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported in this environment")
    assert real_path_key(str(link)) == real_path_key(str(target))


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def test_discover_targets_finds_resources_recursively(tmp_path):
    """Test directories are scanned recursively for resource files."""
    _write(tmp_path / "res" / "a.resource", _resource("A"))
    _write(tmp_path / "res" / "deep" / "nested" / "b.resource", _resource("B"))
    cfg = parse_config(
        {"coverage": {"paths": ["res"]}}, base_dir=str(tmp_path)
    )
    targets = discover_targets(cfg)
    assert [t.display_path for t in targets] == [
        "res/a.resource",
        "res/deep/nested/b.resource",
    ]


def test_discover_targets_distinguishes_same_basename(tmp_path):
    """Test same-named resources in different directories are both measured."""
    _write(tmp_path / "res" / "x" / "common.resource", _resource("A"))
    _write(tmp_path / "res" / "y" / "common.resource", _resource("B"))
    cfg = parse_config(
        {"coverage": {"paths": ["res"]}}, base_dir=str(tmp_path)
    )
    targets = discover_targets(cfg)
    assert len(targets) == 2
    assert {t.display_path for t in targets} == {
        "res/x/common.resource",
        "res/y/common.resource",
    }


def test_discover_targets_applies_exclude(tmp_path):
    """Test excluded paths are not measured."""
    _write(tmp_path / "res" / "keep.resource", _resource("A"))
    _write(tmp_path / "res" / "old" / "drop.resource", _resource("B"))
    cfg = parse_config(
        {"coverage": {"paths": ["res"], "exclude": ["*old*"]}},
        base_dir=str(tmp_path),
    )
    targets = discover_targets(cfg)
    assert [t.display_path for t in targets] == ["res/keep.resource"]


def test_discover_targets_honours_patterns(tmp_path):
    """Test only files matching the configured patterns are collected."""
    _write(tmp_path / "res" / "a.resource", _resource("A"))
    _write(tmp_path / "res" / "b.robot", _resource("B"))
    cfg = parse_config(
        {"coverage": {"paths": ["res"], "patterns": ["*.robot"]}},
        base_dir=str(tmp_path),
    )
    targets = discover_targets(cfg)
    assert [t.display_path for t in targets] == ["res/b.robot"]


def test_discover_targets_override_sets_threshold(tmp_path):
    """Test an explicit entry overrides the global threshold."""
    _write(tmp_path / "res" / "a.resource", _resource("A"))
    cfg = parse_config(
        {
            "coverage": {
                "fail_under": 50.0,
                "paths": ["res"],
                "resources": {"res/a.resource": {"fail_under": 100.0}},
            }
        },
        base_dir=str(tmp_path),
    )
    targets = discover_targets(cfg)
    assert len(targets) == 1
    assert targets[0].fail_under == 100.0


def test_discover_targets_includes_explicit_file_outside_paths(tmp_path):
    """Test explicitly listed files are measured even if outside the paths."""
    _write(tmp_path / "res" / "a.resource", _resource("A"))
    _write(tmp_path / "extra" / "b.resource", _resource("B"))
    cfg = parse_config(
        {
            "coverage": {
                "paths": ["res"],
                "resources": {"extra/b.resource": {"fail_under": 10.0}},
            }
        },
        base_dir=str(tmp_path),
    )
    targets = discover_targets(cfg)
    assert {t.display_path for t in targets} == {
        "res/a.resource",
        "extra/b.resource",
    }


def test_discover_targets_missing_directory(tmp_path):
    """Test a configured path that is not a directory raises."""
    cfg = parse_config(
        {"coverage": {"paths": ["nope"]}}, base_dir=str(tmp_path)
    )
    with pytest.raises(FileNotFoundError, match="not a directory"):
        discover_targets(cfg)


def test_discover_targets_missing_explicit_file(tmp_path):
    """Test an explicitly listed missing file raises."""
    cfg = parse_config(
        {"coverage": {"resources": {"gone.resource": {}}}},
        base_dir=str(tmp_path),
    )
    with pytest.raises(FileNotFoundError, match="Resource file not found"):
        discover_targets(cfg)


# --------------------------------------------------------------------------- #
# Keyword parsing
# --------------------------------------------------------------------------- #
def test_parse_defined_keywords_reads_real_resource():
    """Test defined keywords are parsed from an actual resource file."""
    assert parse_defined_keywords(RESOURCE_1) == [
        "Resource Keyword Test",
        "Resource Keyword Test With Argument",
        "Resource Keyword Test With Named Arguments",
    ]


def test_parse_defined_keywords_missing_file():
    """Test parsing a non-existent resource raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_defined_keywords("does-not-exist.resource")


# --------------------------------------------------------------------------- #
# Coverage computation
# --------------------------------------------------------------------------- #
def _target(abs_path, fail_under=80.0, display=None):
    """Build a ResourceTarget for testing."""
    return ResourceTarget(
        display_path=display or abs_path,
        abs_path=abs_path,
        fail_under=fail_under,
    )


def test_compute_full_coverage():
    """Test a fully exercised resource reports 100% and passes."""
    t = _target("/p/a.resource", 100.0)
    report = compute_coverage(
        [t],
        {normalize_path(t.abs_path): ["Kw A", "Kw B"]},
        {normalize_path(t.abs_path): {"Kw A", "Kw B"}},
        100.0,
    )
    res = report.resources[0]
    assert (res.hit, res.total, res.percent) == (2, 2, 100.0)
    assert res.missed == []
    assert report.passed is True


def test_compute_partial_coverage():
    """Test a partially exercised resource reports missed keywords."""
    t = _target("/p/a.resource", 80.0)
    report = compute_coverage(
        [t],
        {normalize_path(t.abs_path): ["Kw A", "Kw B", "Kw C", "Kw D"]},
        {normalize_path(t.abs_path): {"Kw A", "Kw B"}},
        80.0,
    )
    res = report.resources[0]
    assert (res.hit, res.total, res.percent) == (2, 4, 50.0)
    assert sorted(res.missed) == ["Kw C", "Kw D"]
    assert report.passed is False


def test_resource_without_tests_has_zero_coverage():
    """Test a discovered resource with no executed keywords reports 0%."""
    t = _target("/p/a.resource", 50.0)
    report = compute_coverage(
        [t], {normalize_path(t.abs_path): ["Kw A", "Kw B"]}, {}, 50.0
    )
    res = report.resources[0]
    assert (res.hit, res.percent, res.passed) == (0, 0.0, False)


def test_empty_resource_is_fully_covered():
    """Test a resource defining no keywords is vacuously fully covered."""
    t = _target("/p/empty.resource", 100.0)
    report = compute_coverage(
        [t], {normalize_path(t.abs_path): []}, {}, 100.0
    )
    res = report.resources[0]
    assert (res.total, res.percent, res.passed) == (0, 100.0, True)


def test_same_basename_resources_measured_independently():
    """Test coverage is attributed per file, not per base name."""
    t1 = _target("/p/x/common.resource", 0.0, "x/common.resource")
    t2 = _target("/p/y/common.resource", 0.0, "y/common.resource")
    report = compute_coverage(
        [t1, t2],
        {
            normalize_path(t1.abs_path): ["Only In X"],
            normalize_path(t2.abs_path): ["Only In Y"],
        },
        {normalize_path(t1.abs_path): {"Only In X"}},
        0.0,
    )
    by_path = {r.path: r for r in report.resources}
    assert by_path["x/common.resource"].percent == 100.0
    assert by_path["y/common.resource"].percent == 0.0


def test_executed_keyword_not_defined_is_ignored():
    """Test executed keywords absent from the resource do not inflate hits."""
    t = _target("/p/a.resource", 0.0)
    report = compute_coverage(
        [t],
        {normalize_path(t.abs_path): ["Kw A"]},
        {normalize_path(t.abs_path): {"Kw A", "Other"}},
        0.0,
    )
    assert report.resources[0].hit == 1


def test_global_gate_fails_even_if_each_resource_passes():
    """Test the global threshold can fail the run on its own."""
    t1 = _target("/p/a.resource", 0.0, "a.resource")
    t2 = _target("/p/b.resource", 0.0, "b.resource")
    report = compute_coverage(
        [t1, t2],
        {
            normalize_path(t1.abs_path): ["A1", "A2"],
            normalize_path(t2.abs_path): ["B1", "B2"],
        },
        {
            normalize_path(t1.abs_path): {"A1"},
            normalize_path(t2.abs_path): {"B1"},
        },
        90.0,
    )
    assert all(r.passed for r in report.resources)
    assert report.percent == 50.0
    assert report.passed is False


# --------------------------------------------------------------------------- #
# Report serialisation
# --------------------------------------------------------------------------- #
def test_report_to_dict_structure():
    """Test the JSON report contains totals and covered/missed keywords."""
    t = _target("/p/a.resource", 80.0, "a.resource")
    report = compute_coverage(
        [t],
        {normalize_path(t.abs_path): ["Kw A", "Kw B"]},
        {normalize_path(t.abs_path): {"Kw A"}},
        80.0,
    )
    data = json.loads(json.dumps(report.to_dict()))
    assert data["total"] == {
        "resources": 1,
        "defined": 2,
        "covered": 1,
        "percent": 50.0,
        "fail_under": 80.0,
        "passed": False,
    }
    assert data["resources"][0]["missed_keywords"] == ["Kw B"]
    assert data["resources"][0]["covered_keywords"] == ["Kw A"]


def _two_resource_report():
    """Build a report with one passing and one failing resource."""
    t1 = _target("/p/good.resource", 100.0, "good.resource")
    t2 = _target("/p/bad.resource", 100.0, "bad.resource")
    return compute_coverage(
        [t1, t2],
        {
            normalize_path(t1.abs_path): ["A"],
            normalize_path(t2.abs_path): ["B1", "B2"],
        },
        {
            normalize_path(t1.abs_path): {"A"},
            normalize_path(t2.abs_path): {"B1"},
        },
        80.0,
    )


def test_format_summary_failing_mode_hides_passing_resources():
    """Test the default console mode lists only failing resources."""
    summary = _two_resource_report().format_summary("failing")
    assert "bad.resource" in summary
    assert "good.resource" not in summary
    assert "below threshold (1)" in summary
    assert "TOTAL" in summary


def test_format_summary_all_mode_lists_every_resource():
    """Test 'all' mode lists passing and failing resources alike."""
    summary = _two_resource_report().format_summary("all")
    assert "good.resource" in summary
    assert "bad.resource" in summary
    assert "PASS" in summary
    assert "FAIL" in summary


def test_format_summary_reports_clean_run():
    """Test a fully passing run states all resources met thresholds."""
    t = _target("/p/a.resource", 0.0, "a.resource")
    report = compute_coverage(
        [t],
        {normalize_path(t.abs_path): ["A"]},
        {normalize_path(t.abs_path): {"A"}},
        0.0,
    )
    summary = report.format_summary("failing")
    assert "All 1 resources meet their thresholds." in summary
    assert "1 resources" in summary
