#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = RUN_ROOT.parents[2]
sys.path.insert(0, str(REPO_ROOT))

import black
from black.mode import TargetVersion
from tests.util import all_data_cases, read_data_with_mode

SIZES = (40, 80, 160, 300)
WARMUPS_PER_SIZE = 1
SAMPLES_PER_SIZE = 3
PHASES = {"baseline", "candidate"}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def utc_now() -> str:
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def generated_source(n: int) -> str:
    return "x = a" + "".join(f"[{i}]" for i in range(n)) + "\n"


def mode_payload(mode: black.Mode) -> dict[str, Any]:
    return {
        "target_versions": sorted(version.name for version in mode.target_versions),
        "line_length": mode.line_length,
        "string_normalization": mode.string_normalization,
        "is_pyi": mode.is_pyi,
        "is_ipynb": mode.is_ipynb,
        "skip_source_first_line": mode.skip_source_first_line,
        "magic_trailing_comma": mode.magic_trailing_comma,
        "python_cell_magics": sorted(mode.python_cell_magics),
        "preview": mode.preview,
        "unstable": mode.unstable,
        "enabled_features": sorted(feature.name for feature in mode.enabled_features),
    }


def environment_payload(phase: str) -> dict[str, Any]:
    return {
        "captured_at": utc_now(),
        "phase": phase,
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cwd": str(REPO_ROOT),
        "git_head": git("rev-parse", "HEAD"),
        "git_branch": git("branch", "--show-current"),
        "git_status_short": git("status", "--short"),
        "black_module": str(Path(black.__file__).resolve()),
        "black_version": black.__version__,
        "mode": mode_payload(black.Mode()),
        "NO_COLOR_present": "NO_COLOR" in os.environ,
        "clock": "time.perf_counter",
        "black_cache": (
            "not applicable; black.format_str does not use Black's file cache"
        ),
        "generator": '"x = a" + "".join(f"[{i}]" for i in range(n)) + "\\n"',
        "warmup": (
            f"{WARMUPS_PER_SIZE} unmeasured black.format_str call per n immediately"
            " before samples"
        ),
        "samples_per_n": SAMPLES_PER_SIZE,
        "script": str(Path(__file__).relative_to(REPO_ROOT)),
        "script_sha256": sha256_file(Path(__file__)),
    }


def capture_generated_and_benchmark(phase: str) -> dict[str, Any]:
    phase_dir = RUN_ROOT / phase
    output_dir = phase_dir / "generated-output"
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}

    for n in SIZES:
        source = generated_source(n)
        for _ in range(WARMUPS_PER_SIZE):
            black.format_str(source, mode=black.Mode())

        samples: list[float] = []
        formatted: str | None = None
        for _ in range(SAMPLES_PER_SIZE):
            started = time.perf_counter()
            current = black.format_str(source, mode=black.Mode())
            samples.append(time.perf_counter() - started)
            if formatted is None:
                formatted = current
            elif current != formatted:
                raise AssertionError(f"non-deterministic generated output for n={n}")

        assert formatted is not None
        formatted_bytes = formatted.encode("utf-8")
        output_path = output_dir / f"n-{n}.py"
        output_path.write_bytes(formatted_bytes)
        results[str(n)] = {
            "n": n,
            "source_byte_count": len(source.encode("utf-8")),
            "source_sha256": sha256_bytes(source.encode("utf-8")),
            "output_byte_count": len(formatted_bytes),
            "output_sha256": sha256_bytes(formatted_bytes),
            "output_path": str(output_path.relative_to(REPO_ROOT)),
            "samples_seconds": samples,
            "median_seconds": statistics.median(samples),
            "minimum_seconds": min(samples),
            "maximum_seconds": max(samples),
        }

    benchmark = {
        "schema_version": 1,
        "phase": phase,
        "captured_at": utc_now(),
        "protocol": {
            "api": "black.format_str(source, mode=black.Mode())",
            "generator": '"x = a" + "".join(f"[{i}]" for i in range(n)) + "\\n"',
            "sizes": list(SIZES),
            "warmups_per_size": WARMUPS_PER_SIZE,
            "samples_per_size": SAMPLES_PER_SIZE,
            "clock": "time.perf_counter",
            "cache": "none",
        },
        "results": results,
    }
    write_json(phase_dir / f"benchmark-{phase}.json", benchmark)
    write_json(
        phase_dir / f"generated-output-manifest-{phase}.json",
        {
            "schema_version": 1,
            "phase": phase,
            "captured_at": benchmark["captured_at"],
            "generator": benchmark["protocol"]["generator"],
            "outputs": {
                n: {
                    key: value
                    for key, value in result.items()
                    if key in {
                        "n",
                        "source_byte_count",
                        "source_sha256",
                        "output_byte_count",
                        "output_sha256",
                        "output_path",
                    }
                }
                for n, result in results.items()
            },
        },
    )
    return benchmark


def fixture_variants(subdir: str, name: str) -> list[dict[str, Any]]:
    args, source, expected = read_data_with_mode(subdir, name)
    variants: list[tuple[str, black.Mode, Any, str | None]] = [
        ("declared", args.mode, args.lines, expected)
    ]
    if args.minimum_version is not None:
        major, minor = args.minimum_version
        target = TargetVersion[f"PY{major}{minor}"]
        variants.append((
            f"minimum-target-{target.name}",
            replace(args.mode, target_versions={target}),
            args.lines,
            expected,
        ))

    if args.mode.unstable:
        alternate_mode = replace(args.mode, unstable=False, preview=False)
        alternate_name = "stable-alternate"
    else:
        alternate_mode = replace(args.mode, preview=not args.mode.preview)
        alternate_name = "preview-alternate"
    variants.append((alternate_name, alternate_mode, args.lines, None))
    variants.append((
        "line-length-1-stable",
        replace(args.mode, preview=False, line_length=1, unstable=False),
        args.lines,
        None,
    ))
    if not args.no_preview_line_length_1:
        variants.append((
            "line-length-1-preview",
            replace(args.mode, preview=True, line_length=1, unstable=False),
            args.lines,
            None,
        ))

    entries: list[dict[str, Any]] = []
    for variant_name, mode, lines, exact_expected in variants:
        actual = black.format_str(source, mode=mode, lines=lines)
        actual_bytes = actual.encode("utf-8")
        if exact_expected is not None and actual != exact_expected:
            raise AssertionError(f"fixture mismatch at {subdir}/{name}::{variant_name}")
        entries.append({
            "key": f"{subdir}/{name}::{variant_name}",
            "subdir": subdir,
            "name": name,
            "variant": variant_name,
            "mode": mode_payload(mode),
            "lines": [list(line_range) for line_range in lines],
            "source_byte_count": len(source.encode("utf-8")),
            "source_sha256": sha256_bytes(source.encode("utf-8")),
            "expected_byte_count": (
                len(exact_expected.encode("utf-8"))
                if exact_expected is not None
                else None
            ),
            "expected_sha256": (
                sha256_bytes(exact_expected.encode("utf-8"))
                if exact_expected is not None
                else None
            ),
            "output_byte_count": len(actual_bytes),
            "output_sha256": sha256_bytes(actual_bytes),
        })
    return entries


def capture_fixture_manifest(phase: str) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for subdir in ("cases", "line_ranges_formatted"):
        for name in sorted(all_data_cases(subdir)):
            entries.extend(fixture_variants(subdir, name))
    entries.sort(key=lambda entry: entry["key"])
    manifest = {
        "schema_version": 1,
        "phase": phase,
        "captured_at": utc_now(),
        "loader": "tests.util.all_data_cases + tests.util.read_data_with_mode",
        "fixture_directories": ["cases", "line_ranges_formatted"],
        "variant_policy": (
            "declared flags, minimum target when declared, alternate preview/stable,"
            " and pytest line-length=1 modes"
        ),
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(RUN_ROOT / phase / f"fixture-manifest-{phase}.json", manifest)
    return manifest


def fixture_entry_signature(entry: dict[str, Any]) -> str:
    """Return a stable signature while preserving duplicate loader invocations."""
    return json.dumps(
        {
            "subdir": entry["subdir"],
            "name": entry["name"],
            "variant": entry["variant"],
            "mode": entry["mode"],
            "lines": entry["lines"],
            "source_byte_count": entry["source_byte_count"],
            "source_sha256": entry["source_sha256"],
            "output_byte_count": entry["output_byte_count"],
            "output_sha256": entry["output_sha256"],
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def fixture_groups(entries: list[dict[str, Any]]) -> dict[str, Counter[str]]:
    groups: dict[str, Counter[str]] = {}
    for entry in entries:
        groups.setdefault(entry["key"], Counter())[fixture_entry_signature(entry)] += 1
    return groups


BOUNDARY_SOURCES = {
    "attribute_call_chain": (
        "x = some_extremely_long_root_name.with_a_long_attribute"
        ".another_long_attribute.method_with_a_long_name(argument)"
        ".final_attribute\n"
    ),
    "mixed_subscript_call_trailer": (
        "x = a"
        + "".join(f"[{i}]" for i in range(48))
        + ".method_with_a_long_name(argument).final_attribute\n"
    ),
}


def capture_boundaries(phase: str) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for name, source in BOUNDARY_SOURCES.items():
        output = black.format_str(source, mode=black.Mode())
        output_bytes = output.encode("utf-8")
        entries[name] = {
            "source": source,
            "source_sha256": sha256_bytes(source.encode("utf-8")),
            "output": output,
            "output_byte_count": len(output_bytes),
            "output_sha256": sha256_bytes(output_bytes),
        }
    payload = {
        "schema_version": 1,
        "phase": phase,
        "captured_at": utc_now(),
        "entries": entries,
    }
    write_json(RUN_ROOT / phase / f"boundary-manifest-{phase}.json", payload)
    return payload


def compare_candidate(
    benchmark: dict[str, Any],
    fixtures: dict[str, Any],
    boundaries: dict[str, Any],
) -> dict[str, Any]:
    baseline_dir = RUN_ROOT / "baseline"
    baseline_benchmark = json.loads(
        (baseline_dir / "benchmark-baseline.json").read_text(encoding="utf-8")
    )
    baseline_generated = json.loads(
        (baseline_dir / "generated-output-manifest-baseline.json").read_text(
            encoding="utf-8"
        )
    )
    candidate_generated = json.loads(
        (RUN_ROOT / "candidate" / "generated-output-manifest-candidate.json").read_text(
            encoding="utf-8"
        )
    )
    baseline_fixtures = json.loads(
        (baseline_dir / "fixture-manifest-baseline.json").read_text(encoding="utf-8")
    )
    baseline_boundaries = json.loads(
        (baseline_dir / "boundary-manifest-baseline.json").read_text(encoding="utf-8")
    )

    generated_comparisons: dict[str, Any] = {}
    generated_identity = True
    for n in map(str, SIZES):
        before = baseline_generated["outputs"][n]
        after = candidate_generated["outputs"][n]
        before_bytes = (REPO_ROOT / before["output_path"]).read_bytes()
        after_bytes = (REPO_ROOT / after["output_path"]).read_bytes()
        identical = (
            before["output_sha256"] == after["output_sha256"]
            and before["output_byte_count"] == after["output_byte_count"]
            and before_bytes == after_bytes
        )
        generated_identity &= identical
        generated_comparisons[n] = {
            "identical": identical,
            "baseline_sha256": before["output_sha256"],
            "candidate_sha256": after["output_sha256"],
            "baseline_byte_count": before["output_byte_count"],
            "candidate_byte_count": after["output_byte_count"],
        }

    before_fixture_groups = fixture_groups(baseline_fixtures["entries"])
    after_fixture_groups = fixture_groups(fixtures["entries"])
    removed_fixture_keys = sorted(
        before_fixture_groups.keys() - after_fixture_groups.keys()
    )
    added_fixture_keys = sorted(
        after_fixture_groups.keys() - before_fixture_groups.keys()
    )
    changed_fixture_keys = sorted(
        key
        for key in before_fixture_groups.keys() & after_fixture_groups.keys()
        if before_fixture_groups[key] - after_fixture_groups[key]
    )
    unmatched_baseline_entries = sum(
        sum(
            (
                before_fixture_groups[key] - after_fixture_groups.get(key, Counter())
            ).values()
        )
        for key in before_fixture_groups
    )
    duplicate_baseline_entries = len(baseline_fixtures["entries"]) - len(
        before_fixture_groups
    )
    duplicate_candidate_entries = len(fixtures["entries"]) - len(after_fixture_groups)
    fixture_identity = unmatched_baseline_entries == 0

    boundary_comparisons: dict[str, Any] = {}
    boundary_identity = True
    for name, before in baseline_boundaries["entries"].items():
        after = boundaries["entries"][name]
        identical = (
            before["output_sha256"] == after["output_sha256"]
            and before["output_byte_count"] == after["output_byte_count"]
            and before["output"] == after["output"]
        )
        boundary_identity &= identical
        boundary_comparisons[name] = {
            "identical": identical,
            "baseline_sha256": before["output_sha256"],
            "candidate_sha256": after["output_sha256"],
        }

    before_160 = baseline_benchmark["results"]["160"]["median_seconds"]
    after_160 = benchmark["results"]["160"]["median_seconds"]
    after_300 = benchmark["results"]["300"]["median_seconds"]
    speedup_160 = before_160 / after_160
    growth_ratio = after_300 / after_160
    size_ratio = 300 / 160
    growth_exponent = math.log(growth_ratio) / math.log(size_ratio)
    performance_pass = speedup_160 >= 10 and growth_exponent < 1.5

    comparison = {
        "schema_version": 1,
        "captured_at": utc_now(),
        "generated_identity": generated_identity,
        "generated_comparisons": generated_comparisons,
        "fixture_identity_for_all_preexisting_entries": fixture_identity,
        "baseline_fixture_entry_count": len(baseline_fixtures["entries"]),
        "candidate_fixture_entry_count": len(fixtures["entries"]),
        "baseline_fixture_unique_key_count": len(before_fixture_groups),
        "candidate_fixture_unique_key_count": len(after_fixture_groups),
        "baseline_fixture_duplicate_entry_count": duplicate_baseline_entries,
        "candidate_fixture_duplicate_entry_count": duplicate_candidate_entries,
        "unmatched_baseline_fixture_entry_count": unmatched_baseline_entries,
        "removed_fixture_keys": removed_fixture_keys,
        "added_fixture_keys": added_fixture_keys,
        "changed_fixture_keys": changed_fixture_keys,
        "boundary_identity": boundary_identity,
        "boundary_comparisons": boundary_comparisons,
        "performance": {
            "baseline_n160_median_seconds": before_160,
            "candidate_n160_median_seconds": after_160,
            "n160_speedup": speedup_160,
            "candidate_n300_median_seconds": after_300,
            "candidate_n300_to_n160_time_ratio": growth_ratio,
            "n300_to_n160_size_ratio": size_ratio,
            "observed_growth_exponent": growth_exponent,
            "nonquadratic_threshold": "observed exponent < 1.5 between n=160 and n=300",
            "pass": performance_pass,
        },
        "pass": (
            generated_identity
            and fixture_identity
            and boundary_identity
            and performance_pass
        ),
    }
    write_json(RUN_ROOT / "candidate" / "candidate-comparison.json", comparison)
    if not comparison["pass"]:
        raise AssertionError("candidate evidence comparison failed")
    return comparison


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=sorted(PHASES))
    args = parser.parse_args()
    phase = args.phase
    phase_dir = RUN_ROOT / phase
    phase_dir.mkdir(parents=True, exist_ok=True)

    environment = environment_payload(phase)
    write_json(phase_dir / f"environment-{phase}.json", environment)
    benchmark = capture_generated_and_benchmark(phase)
    fixtures = capture_fixture_manifest(phase)
    boundaries = capture_boundaries(phase)

    summary: dict[str, Any] = {
        "phase": phase,
        "environment": str(
            (phase_dir / f"environment-{phase}.json").relative_to(REPO_ROOT)
        ),
        "benchmark": str(
            (phase_dir / f"benchmark-{phase}.json").relative_to(REPO_ROOT)
        ),
        "generated_manifest": str(
            (phase_dir / f"generated-output-manifest-{phase}.json").relative_to(
                REPO_ROOT
            )
        ),
        "fixture_manifest": str(
            (phase_dir / f"fixture-manifest-{phase}.json").relative_to(REPO_ROOT)
        ),
        "fixture_entries": fixtures["entry_count"],
        "boundary_manifest": str(
            (phase_dir / f"boundary-manifest-{phase}.json").relative_to(REPO_ROOT)
        ),
        "medians_seconds": {
            n: result["median_seconds"] for n, result in benchmark["results"].items()
        },
    }
    if phase == "candidate":
        summary["comparison"] = compare_candidate(benchmark, fixtures, boundaries)
    write_json(phase_dir / f"summary-{phase}.json", summary)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
