"""Validate a captured model-baseline JSONL without running a verifier.

The validator checks provenance and split membership only. It deliberately does
not interpret a completion as verified C; that is the job of the pinned
Docker/Frama-C replay.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REQUIRED = {
    "task_id",
    "source_idx",
    "split",
    "model",
    "revision",
    "prompt_tokens",
    "completion_tokens",
    "elapsed_seconds",
    "completion",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--split-manifest", type=Path, required=True)
    parser.add_argument("--split", default="validation")
    args = parser.parse_args()

    manifest = json.loads(args.split_manifest.read_text(encoding="utf-8"))
    try:
        allowed = set(manifest["splits"][args.split])
    except KeyError as exc:
        parser.error(f"unknown split {args.split!r}: {exc}")

    rows = [
        json.loads(line)
        for line in args.baseline.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not rows:
        raise SystemExit("baseline is empty")

    seen: set[str] = set()
    models: set[str] = set()
    revisions: set[str] = set()
    for number, row in enumerate(rows, start=1):
        missing = REQUIRED - row.keys()
        if missing:
            raise SystemExit(f"row {number} missing fields: {sorted(missing)}")
        task_id = row["task_id"]
        if not isinstance(task_id, str) or task_id not in allowed:
            raise SystemExit(
                f"row {number} task_id is not in {args.split}: {task_id!r}"
            )
        if task_id in seen:
            raise SystemExit(f"duplicate task_id at row {number}: {task_id}")
        if row["split"] != args.split:
            raise SystemExit(f"row {number} has split {row['split']!r}")
        for field in ("prompt_tokens", "completion_tokens"):
            if not isinstance(row[field], int) or row[field] < 0:
                raise SystemExit(f"row {number} has invalid {field}")
        if (
            not isinstance(row["elapsed_seconds"], (int, float))
            or row["elapsed_seconds"] < 0
        ):
            raise SystemExit(f"row {number} has invalid elapsed_seconds")
        if not isinstance(row["completion"], str):
            raise SystemExit(f"row {number} completion is not text")
        seen.add(task_id)
        models.add(row["model"])
        revisions.add(row["revision"])

    if len(models) != 1 or len(revisions) != 1:
        raise SystemExit(
            f"mixed model provenance: models={models}, revisions={revisions}"
        )
    print(
        json.dumps(
            {
                "status": "valid",
                "rows": len(rows),
                "split": args.split,
                "model": next(iter(models)),
                "revision": next(iter(revisions)),
                "completion_tokens": sum(row["completion_tokens"] for row in rows),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
