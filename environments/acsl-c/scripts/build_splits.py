#!/usr/bin/env python3
"""Build deterministic, leakage-audited research splits.

The historical ``casp_eval.jsonl`` has already been used for model selection, so
it becomes the development/validation set.  A fresh stratified test set is carved
from the original training file.  Legacy vacuity-unknown rows and normalized
duplicates are excluded rather than silently assigned.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from acsl_c.integrity import check_fixed_task_integrity


def stable_id(record: dict) -> str:
    source = record.get("reference_solution") or record.get("skeleton_c") or ""
    digest = hashlib.sha256(source.replace("\r\n", "\n").encode()).hexdigest()
    return f"casp-sha256:{digest}"


def eligible(record: dict) -> bool:
    value = record.get("non_vacuous")
    if int(record.get("data_schema_version", 1)) >= 2:
        return value is True
    return value is False


def structurally_valid(record: dict) -> bool:
    if record.get("mode", "hints") != "hints":
        return True
    reference = record.get("reference_solution")
    skeleton = record.get("skeleton_c")
    return bool(
        reference and skeleton and check_fixed_task_integrity(reference, skeleton).ok
    )


def difficulty(vc: int) -> str:
    if vc <= 8:
        return "easy"
    if vc <= 20:
        return "medium"
    if vc <= 40:
        return "hard"
    return "extreme"


def features(record: dict) -> list[str]:
    source = record.get("reference_solution") or record.get("skeleton_c") or ""
    lowered = source.lower()
    result = []
    checks = {
        "loop": r"\b(for|while|do)\b",
        "pointer": r"\*\s*[A-Za-z_]|\\valid|->",
        "array": r"\[[^\]]*\]|\\valid\([^)]*\.\.",
        "quantifier": r"\\(forall|exists|sum|lambda)\b",
        "multi_function": r"\)\s*\{[\s\S]*\)\s*\{",
    }
    for name, pattern in checks.items():
        if re.search(pattern, lowered):
            result.append(name)
    return result


def dedupe_key(record: dict) -> str:
    skeleton = record.get("skeleton_c") or record.get("reference_solution") or ""
    normalized = re.sub(r"\s+", "", skeleton.replace("//TODO:complete", ""))
    return hashlib.sha256(normalized.encode()).hexdigest()


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def distributions(records: list[dict]) -> dict:
    return {
        "difficulty": dict(
            Counter(difficulty(int(row.get("vc_estimate", 0))) for row in records)
        ),
        "features": dict(
            Counter(feature for row in records for feature in features(row))
        ),
    }


def choose_stratified(records: list[dict], count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    strata: dict[tuple[str, tuple[str, ...]], list[dict]] = defaultdict(list)
    for row in records:
        major = tuple(
            name
            for name in ("loop", "pointer", "array", "quantifier")
            if name in features(row)
        )
        strata[(difficulty(int(row.get("vc_estimate", 0))), major)].append(row)
    for rows in strata.values():
        rows.sort(key=stable_id)
        rng.shuffle(rows)

    selected: list[dict] = []
    allocations = []
    total = len(records)
    for key, rows in strata.items():
        exact = count * len(rows) / total
        take = min(len(rows), int(exact))
        selected.extend(rows[:take])
        allocations.append((exact - take, key, rows, take))
    for _, _, rows, taken in sorted(allocations, reverse=True):
        if len(selected) >= count:
            break
        if taken < len(rows):
            selected.append(rows[taken])
    if len(selected) < count:
        chosen = {stable_id(row) for row in selected}
        remainder = [row for row in records if stable_id(row) not in chosen]
        rng.shuffle(remainder)
        selected.extend(remainder[: count - len(selected)])
    return selected[:count]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir", default=str(Path(__file__).parent.parent / "data")
    )
    parser.add_argument("--test-size", type=int, default=48)
    parser.add_argument("--seed", type=int, default=20260909)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    historical_eval = load_jsonl(data_dir / "casp_eval.jsonl")
    historical_train = load_jsonl(data_dir / "casp_train.jsonl")
    replay_exclusions_path = data_dir / "replay_exclusions.jsonl"
    replay_exclusions = {
        row["stable_id"]: row
        for row in (
            load_jsonl(replay_exclusions_path)
            if replay_exclusions_path.exists()
            else []
        )
    }
    excluded = []
    candidates = []
    for origin, rows in (
        ("historical_eval", historical_eval),
        ("historical_train", historical_train),
    ):
        for row in rows:
            row_id = stable_id(row)
            if row_id in replay_exclusions:
                excluded.append(
                    {
                        "stable_id": row_id,
                        "origin": origin,
                        "reason": replay_exclusions[row_id]["reason"],
                    }
                )
            elif not eligible(row):
                excluded.append(
                    {
                        "stable_id": row_id,
                        "origin": origin,
                        "reason": "vacuity-unknown",
                    }
                )
            elif not structurally_valid(row):
                excluded.append(
                    {
                        "stable_id": row_id,
                        "origin": origin,
                        "reason": "invalid-body-extraction",
                    }
                )
            else:
                row = {**row, "_origin": origin}
                candidates.append(row)

    groups: dict[str, list[dict]] = defaultdict(list)
    for row in candidates:
        groups[dedupe_key(row)].append(row)
    deduplicated = []
    duplicate_groups = []
    for rows in groups.values():
        rows.sort(key=lambda row: (row["_origin"] != "historical_eval", stable_id(row)))
        deduplicated.append(rows[0])
        if len(rows) > 1:
            duplicate_groups.append([stable_id(row) for row in rows])
            for row in rows[1:]:
                excluded.append(
                    {
                        "stable_id": stable_id(row),
                        "origin": row["_origin"],
                        "reason": f"duplicate-of:{stable_id(rows[0])}",
                    }
                )

    validation = [row for row in deduplicated if row["_origin"] == "historical_eval"]
    train_pool = [row for row in deduplicated if row["_origin"] == "historical_train"]
    test = choose_stratified(
        train_pool, min(args.test_size, len(train_pool)), args.seed
    )
    test_ids = {stable_id(row) for row in test}
    train = [row for row in train_pool if stable_id(row) not in test_ids]

    manifest = {
        "schema_version": 1,
        "seed": args.seed,
        "policy": {
            "validation": "historical CASP eval split; development-only because baselines used it",
            "test": "fresh deterministic stratified sample from historical train split",
            "train": "remaining eligible, deduplicated historical train rows",
            "eligibility": "verified and conclusively non-vacuous; vacuity-unknown excluded",
        },
        "splits": {
            "train": sorted(stable_id(row) for row in train),
            "validation": sorted(stable_id(row) for row in validation),
            "test": sorted(test_ids),
            "all": sorted(stable_id(row) for row in deduplicated),
        },
        "counts": {
            "train": len(train),
            "validation": len(validation),
            "test": len(test),
            "excluded": len(excluded),
            "duplicate_groups": len(duplicate_groups),
        },
        "distributions": {
            "train": distributions(train),
            "validation": distributions(validation),
            "test": distributions(test),
        },
        "excluded": sorted(excluded, key=lambda item: item["stable_id"]),
        "duplicate_groups": duplicate_groups,
    }
    output = data_dir / "split_manifest.json"
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["counts"], indent=2))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
