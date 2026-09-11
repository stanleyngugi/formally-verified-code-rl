"""Provenance validation for redistributable ACSL-C data packs."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

SPDX_RE = re.compile(r"^[A-Za-z0-9.+-]+(?:\s+(?:AND|OR|WITH)\s+[A-Za-z0-9.+-]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FINAL_REVIEW_STATES = {"human-reviewed", "expert-reviewed"}
PROJECT_SOURCE_KINDS = {"project-authored", "third-party"}

REQUIRED_FIELDS = (
    "dataset_id",
    "dataset_version",
    "source_kind",
    "source_repository_url",
    "source_revision",
    "source_path",
    "source_content_sha256",
    "license_spdx",
    "copyright_notice",
    "transformation_description",
    "semantic_family",
    "derivation_family",
    "review_status",
)


@dataclass(frozen=True)
class ProvenanceIssue:
    record: str
    field: str
    message: str


def source_sha256(record: dict) -> str:
    source = record.get("reference_solution") or record.get("skeleton_c") or ""
    return hashlib.sha256(source.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def validate_record_provenance(
    record: dict, *, final_release: bool = False
) -> list[ProvenanceIssue]:
    record_name = str(record.get("stable_id") or record.get("name") or "<unknown>")
    issues: list[ProvenanceIssue] = []
    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                ProvenanceIssue(record_name, field, "missing non-empty string")
            )

    source_kind = record.get("source_kind")
    if isinstance(source_kind, str) and source_kind not in PROJECT_SOURCE_KINDS:
        issues.append(
            ProvenanceIssue(
                record_name,
                "source_kind",
                f"must be one of {sorted(PROJECT_SOURCE_KINDS)}",
            )
        )

    for field in ("skeleton_c", "reference_solution"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            issues.append(
                ProvenanceIssue(record_name, field, "missing non-empty source text")
            )
    negatives = record.get("negative_cases")
    if not isinstance(negatives, list) or not negatives:
        issues.append(
            ProvenanceIssue(
                record_name, "negative_cases", "at least one negative case is required"
            )
        )

    spdx = record.get("license_spdx")
    if isinstance(spdx, str) and spdx and not SPDX_RE.fullmatch(spdx):
        issues.append(
            ProvenanceIssue(
                record_name, "license_spdx", "invalid or unsupported SPDX expression"
            )
        )

    declared_hash = record.get("source_content_sha256")
    if isinstance(declared_hash, str) and declared_hash:
        if not SHA256_RE.fullmatch(declared_hash):
            issues.append(
                ProvenanceIssue(
                    record_name, "source_content_sha256", "must be lowercase SHA-256"
                )
            )
        elif declared_hash != source_sha256(record):
            issues.append(
                ProvenanceIssue(
                    record_name,
                    "source_content_sha256",
                    "does not match normalized reference_solution content",
                )
            )

    if final_release:
        for field in ("source_repository_url", "source_revision", "review_status"):
            value = str(record.get(field, "")).lower()
            if "pending" in value or "worktree" in value or "draft" in value:
                issues.append(
                    ProvenanceIssue(
                        record_name, field, "contains a pre-release placeholder"
                    )
                )
        if record.get("review_status") not in FINAL_REVIEW_STATES:
            issues.append(
                ProvenanceIssue(
                    record_name,
                    "review_status",
                    f"final release requires one of {sorted(FINAL_REVIEW_STATES)}",
                )
            )
    return issues


def iter_jsonl_records(pack_dir: Path) -> list[tuple[Path, int, dict]]:
    records: list[tuple[Path, int, dict]] = []
    for path in sorted(pack_dir.glob("*.jsonl")):
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if line.strip():
                records.append((path, line_number, json.loads(line)))
    return records


def validate_pack(
    pack_dir: Path, *, final_release: bool = False
) -> list[ProvenanceIssue]:
    issues: list[ProvenanceIssue] = []
    records = iter_jsonl_records(pack_dir)
    if not records:
        return [
            ProvenanceIssue(str(pack_dir), "records", "pack contains no JSONL records")
        ]
    for path, line_number, record in records:
        for issue in validate_record_provenance(record, final_release=final_release):
            issues.append(
                ProvenanceIssue(
                    f"{path.name}:{line_number}:{issue.record}",
                    issue.field,
                    issue.message,
                )
            )
    return issues


__all__ = [
    "FINAL_REVIEW_STATES",
    "REQUIRED_FIELDS",
    "ProvenanceIssue",
    "iter_jsonl_records",
    "source_sha256",
    "validate_pack",
    "validate_record_provenance",
]
