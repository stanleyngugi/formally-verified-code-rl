"""Execute offline negative spectests and emit strict evidence JSONL.

Each input record must be a JSON object with ``id`` and ``source`` fields. A
negative spectest is considered rejected only when Frama-C parses and compiles
it, creates at least one goal, finishes without timeout/crash, and does *not*
fully prove the source. Infrastructure failures remain visible but cannot earn
specification-strength reward.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from acsl_c.framac import parse


def execute(record: dict, *, framac_bin: str, provers: str, timeout: int) -> dict:
    expected = record.get("expect_rejected")
    policy = {
        "framac_bin": framac_bin,
        "provers": provers,
        "timeout_seconds": timeout,
        "runner": "frama-c-wp-rte-spectest-v3",
    }
    source = record.get("source")
    if not isinstance(source, str) or not source.strip():
        return {
            "id": record.get("id"),
            "executed": False,
            "rejected": False,
            "expected_rejected": expected,
            "matched_expectation": False,
            "policy": policy,
            "error": "missing source",
        }

    with tempfile.TemporaryDirectory(prefix="acsl_spectest_") as directory:
        root = Path(directory)
        source_path = root / "spectest.c"
        report_path = root / "report.json"
        source_path.write_text(source, encoding="utf-8")
        command = [
            framac_bin,
            "-wp",
            "-wp-rte",
            "-wp-cache",
            "none",
            "-wp-prover",
            provers,
            "-wp-timeout",
            str(timeout),
            "-wp-report-json",
            str(report_path),
            str(source_path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout * 12 + 30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {
                "id": record.get("id"),
                "executed": False,
                "rejected": False,
                "expected_rejected": expected,
                "matched_expectation": False,
                "policy": policy,
                "error": f"{type(exc).__name__}: {exc}",
            }
        payload = (
            report_path.read_text(encoding="utf-8") if report_path.exists() else None
        )
        verdict = parse(payload, completed.stdout)
        verdict.exit_code = completed.returncode
        if completed.stderr and not verdict.stderr_tail:
            verdict.stderr_tail = completed.stderr[-2000:]
        clean = (
            verdict.parse_ok
            and verdict.compiled
            and verdict.goals_total > 0
            and verdict.timeouts == 0
            and verdict.crash is None
        )
        rejected = bool(clean and not verdict.ok)
        return {
            "id": record.get("id"),
            "executed": True,
            "rejected": rejected,
            "expected_rejected": expected,
            "matched_expectation": (
                isinstance(expected, bool) and rejected is expected
            ),
            "verdict": verdict.to_dict(),
            "policy": policy,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--framac-bin", default="frama-c")
    parser.add_argument("--provers", default="alt-ergo,z3")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument(
        "--from-task-records",
        action="store_true",
        help="expand each task record's negative_cases into executable spectests",
    )
    parser.add_argument(
        "--require-expectations",
        action="store_true",
        help="exit nonzero unless every record declares and matches expect_rejected",
    )
    args = parser.parse_args()

    loaded = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if args.from_task_records:
        records = []
        for task in loaded:
            for negative in task.get("negative_cases", []):
                records.append(
                    {
                        "id": f"{task.get('stable_id')}:{negative.get('name', 'negative')}",
                        "source": negative.get("candidate_source"),
                        "expect_rejected": negative.get("expected")
                        == "verification-failure",
                    }
                )
    else:
        records = loaded
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = [
        execute(
            record,
            framac_bin=args.framac_bin,
            provers=args.provers,
            timeout=args.timeout,
        )
        for record in records
    ]
    with args.output.open("w", encoding="utf-8") as stream:
        for result in results:
            stream.write(json.dumps(result) + "\n")
    if args.require_expectations and not all(
        result.get("matched_expectation") for result in results
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
