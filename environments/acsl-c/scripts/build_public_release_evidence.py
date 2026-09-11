#!/usr/bin/env python3
"""Build a fail-closed evidence summary for the redistributable Core-v1 wheel."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--reference-summary", type=Path, required=True)
    parser.add_argument("--negative-evidence", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--unit-tests", type=int, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    replay = json.loads(args.reference_summary.read_text(encoding="utf-8"))
    negatives = jsonl(args.negative_evidence)
    expected = sum(manifest["counts"].values())

    reference_ok = (
        replay["expected"] == expected
        and replay["completed"] == expected
        and replay["fully_proved"] == expected
        and replay["goals_proved"] == replay["goals_total"]
        and replay["rte_proved"] == replay["rte_total"]
        and replay["solver_timeouts"] == 0
    )
    negatives_ok = (
        len(negatives) == expected
        and all(item.get("rejected") is True for item in negatives)
        and all(item.get("matched_expectation") is True for item in negatives)
        and all(item.get("verdict", {}).get("timeouts") == 0 for item in negatives)
    )
    with zipfile.ZipFile(args.wheel) as archive:
        wheel_members = archive.namelist()
    bundled_records = [
        member
        for member in wheel_members
        if member.endswith("/data/packs/core-v1/tasks.jsonl")
    ]
    forbidden = [
        member
        for member in wheel_members
        if "casp" in member.lower() and "/data/" in member.replace("\\", "/")
    ]
    wheel_ok = len(bundled_records) == 1 and not forbidden
    technical_ready = reference_ok and negatives_ok and wheel_ok

    report = {
        "schema": "acsl-c-public-release-evidence-v1",
        "date": datetime.now(UTC).date().isoformat(),
        "dataset": {
            "id": manifest["dataset_id"],
            "version": manifest["dataset_version"],
            "tasks": expected,
            "splits": manifest["counts"],
            "manifest_sha256": sha256(args.manifest),
        },
        "reference_replay": {
            "ok": reference_ok,
            "fully_proved": replay["fully_proved"],
            "goals_proved": replay["goals_proved"],
            "goals_total": replay["goals_total"],
            "rte_proved": replay["rte_proved"],
            "rte_total": replay["rte_total"],
            "solver_timeouts": replay["solver_timeouts"],
            "tool_versions": replay["tool_versions"],
            "artifact_sha256": sha256(args.reference_summary),
        },
        "negative_evidence": {
            "ok": negatives_ok,
            "executed": len(negatives),
            "cleanly_rejected": sum(item.get("rejected") is True for item in negatives),
            "solver_timeouts": sum(
                item.get("verdict", {}).get("timeouts", 0) for item in negatives
            ),
            "policy": "Frama-C WP+RTE with built-in Qed simplifier",
            "artifact_sha256": sha256(args.negative_evidence),
        },
        "package": {
            "ok": wheel_ok,
            "wheel": args.wheel.name,
            "wheel_sha256": sha256(args.wheel),
            "wheel_size_bytes": args.wheel.stat().st_size,
            "bundles_core_v1": len(bundled_records) == 1,
            "bundles_casp_data": bool(forbidden),
        },
        "tests": {"passed": args.unit_tests},
        "technical_release_gate": technical_ready,
        "human_review_gate": False,
        "release_stage": "alpha-machine-verified-awaiting-independent-human-review",
        "claim_boundary": (
            "Environment and Core-v1 machine-verification gates pass. This record does "
            "not claim model improvement, comprehensive C coverage, or independent human review."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if technical_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
