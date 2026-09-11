#!/usr/bin/env python3
"""Fail closed unless an ACSL-C public data pack has complete provenance."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

from acsl_c.provenance import validate_pack

FORBIDDEN_PUBLIC_MARKERS = ("casp", "nicher92/casp", "casp_source_files")
FORBIDDEN_SOURCE_PREFIXES = (
    "data/baselines/",
    "data/quarantine/",
    "data_prev/",
    "data_vacdemo/",
    "data/train_only/",
    "examples/",
)
FORBIDDEN_SOURCE_PATHS = {
    "data/casp_eval.jsonl",
    "data/casp_train.jsonl",
    "data/ingest_report.json",
    "data/replay_exclusions.jsonl",
    "data/split_manifest.json",
}
DATA_SUFFIXES = {".json", ".jsonl"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-dir", type=Path, required=True)
    parser.add_argument("--wheel", type=Path)
    parser.add_argument(
        "--source-root",
        type=Path,
        help="Extracted Prime source archive (or equivalent directory) to audit.",
    )
    parser.add_argument("--final-release", action="store_true")
    parser.add_argument("--report", type=Path)
    return parser.parse_args()


def wheel_issues(path: Path) -> list[str]:
    issues: list[str] = []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        for name in names:
            lowered = name.lower()
            if any(marker in lowered for marker in FORBIDDEN_PUBLIC_MARKERS):
                issues.append(f"forbidden research marker in wheel path: {name}")
        for name in names:
            normalized = name.replace("\\", "/").lower()
            if "/data/" not in normalized or not normalized.endswith(
                (".json", ".jsonl")
            ):
                continue
            payload = archive.read(name).decode("utf-8", errors="ignore").lower()
            for marker in FORBIDDEN_PUBLIC_MARKERS:
                if marker in payload:
                    issues.append(
                        f"forbidden research marker {marker!r} in wheel member: {name}"
                    )
                    break
    return sorted(set(issues))


def source_issues(path: Path) -> list[str]:
    """Reject research corpora and corpus markers in a distributable source tree."""
    issues: list[str] = []
    for candidate in sorted(path.rglob("*")):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(path).as_posix()
        lowered = relative.lower()
        if lowered in FORBIDDEN_SOURCE_PATHS or any(
            lowered.startswith(prefix) for prefix in FORBIDDEN_SOURCE_PREFIXES
        ):
            issues.append(f"forbidden research path in source archive: {relative}")
            continue
        if candidate.suffix.lower() not in DATA_SUFFIXES:
            continue
        # CASP-related implementation notes and negative assertions in evidence
        # are legitimate. Scan only distributable dataset payloads here.
        if not lowered.startswith("data/"):
            continue
        payload = candidate.read_text(encoding="utf-8", errors="ignore").lower()
        for marker in FORBIDDEN_PUBLIC_MARKERS:
            if marker in payload:
                issues.append(
                    f"forbidden research marker {marker!r} in source member: {relative}"
                )
                break
    return sorted(set(issues))


def main() -> int:
    args = parse_args()
    provenance = validate_pack(args.pack_dir, final_release=args.final_release)
    wheel = wheel_issues(args.wheel) if args.wheel else []
    source = source_issues(args.source_root) if args.source_root else []
    report = {
        "schema_version": 1,
        "pack_dir": str(args.pack_dir.resolve()),
        "final_release": args.final_release,
        "provenance_issues": [issue.__dict__ for issue in provenance],
        "wheel_issues": wheel,
        "source_issues": source,
        "ok": not provenance and not wheel and not source,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
