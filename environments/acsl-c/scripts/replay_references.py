#!/usr/bin/env python3
"""Replay manifest-selected reference solutions with the pinned Frama-C judge.

The JSONL output is append-only while work is in progress and can be resumed.
Only records produced with the same replay policy are reused.  A final summary
captures coverage, proof totals, failures, and the tool versions that generated
the evidence.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from acsl_c.framac import Verdict, parse

SCRIPT_VERSION = 1
DEFAULT_FLAGS = (
    "-wp",
    "-wp-rte",
    "-wp-cache",
    "none",
    "-wp-prover",
    "alt-ergo,z3",
    "-wp-timeout",
    "20",
)


def stable_id(record: dict) -> str:
    explicit = record.get("stable_id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    source = record.get("reference_solution") or record.get("skeleton_c") or ""
    digest = hashlib.sha256(source.replace("\r\n", "\n").encode()).hexdigest()
    return f"casp-sha256:{digest}"


def load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def command_output(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr).strip()
    return output if result.returncode == 0 else None


def replay_one(
    record: dict, *, framac_bin: str, flags: tuple[str, ...], wall_timeout: int
) -> dict:
    task_id = stable_id(record)
    source = record.get("reference_solution")
    started = time.monotonic()
    if not isinstance(source, str) or not source.strip():
        return {
            "stable_id": task_id,
            "provenance": record.get("provenance"),
            "duration_seconds": 0.0,
            "verdict": Verdict(ok=False, crash="missing reference_solution").to_dict(),
        }

    with tempfile.TemporaryDirectory(prefix="acslc_replay_") as directory:
        source_path = Path(directory) / "solution.c"
        report_path = Path(directory) / "wp-report.json"
        source_path.write_text(source, encoding="utf-8")
        command = [
            framac_bin,
            *flags,
            "-wp-report-json",
            str(report_path),
            str(source_path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=wall_timeout,
                check=False,
            )
            payload = (
                report_path.read_text(encoding="utf-8")
                if report_path.exists()
                else None
            )
            verdict = parse(payload, result.stdout)
            verdict.exit_code = result.returncode
            verdict.stdout_tail = result.stdout[-2000:]
            verdict.stderr_tail = result.stderr[-2000:]
        except subprocess.TimeoutExpired as exc:
            verdict = Verdict(
                ok=False,
                crash=f"wall-clock timeout after {wall_timeout}s",
                stdout_tail=(exc.stdout or "")[-2000:]
                if isinstance(exc.stdout, str)
                else "",
                stderr_tail=(exc.stderr or "")[-2000:]
                if isinstance(exc.stderr, str)
                else "",
            )
        except OSError as exc:
            verdict = Verdict(ok=False, crash=f"{type(exc).__name__}: {exc}")

    return {
        "stable_id": task_id,
        "provenance": record.get("provenance"),
        "source_sha256": hashlib.sha256(
            source.replace("\r\n", "\n").encode()
        ).hexdigest(),
        "duration_seconds": round(time.monotonic() - started, 3),
        "verdict": verdict.to_dict(),
    }


def summarize(
    *, selected_ids: list[str], results: dict[str, dict], policy: dict, split: str
) -> dict:
    selected = [results[task_id] for task_id in selected_ids if task_id in results]
    failure_kinds: Counter[str] = Counter()
    for row in selected:
        verdict = row["verdict"]
        if verdict.get("ok"):
            continue
        if verdict.get("crash"):
            failure_kinds["crash"] += 1
        elif not verdict.get("parse_ok") or not verdict.get("compiled"):
            failure_kinds["parse_or_compile"] += 1
        elif verdict.get("timeouts"):
            failure_kinds["solver_timeout"] += 1
        else:
            failure_kinds["unproved"] += 1
    return {
        "schema": "acsl-c-reference-replay-summary-v1",
        "script_version": SCRIPT_VERSION,
        "split": split,
        "expected": len(selected_ids),
        "completed": len(selected),
        "fully_proved": sum(bool(row["verdict"].get("ok")) for row in selected),
        "goals_proved": sum(
            int(row["verdict"].get("goals_proved", 0)) for row in selected
        ),
        "goals_total": sum(
            int(row["verdict"].get("goals_total", 0)) for row in selected
        ),
        "rte_proved": sum(int(row["verdict"].get("rte_proved", 0)) for row in selected),
        "rte_total": sum(int(row["verdict"].get("rte_total", 0)) for row in selected),
        "solver_timeouts": sum(
            int(row["verdict"].get("timeouts", 0)) for row in selected
        ),
        "failure_kinds": dict(failure_kinds),
        "duration_seconds": round(
            sum(float(row["duration_seconds"]) for row in selected), 3
        ),
        "policy": policy,
        "tool_versions": {
            "frama_c": command_output([policy["framac_bin"], "-version"]),
            "why3": command_output(["why3", "--version"]),
            "alt_ergo": command_output(["alt-ergo", "--version"]),
            "z3": command_output(["z3", "--version"]),
        },
    }


def main() -> int:
    env_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=env_root / "data")
    parser.add_argument("--data-glob", default="*.jsonl")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--split", choices=("train", "validation", "test", "all"), default="all"
    )
    parser.add_argument(
        "--task-id",
        action="append",
        help="replay only this manifest task ID (repeatable)",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--framac-bin", default=os.environ.get("FRAMAC_BIN", "frama-c"))
    parser.add_argument(
        "--provers", default=os.environ.get("ACSL_PROVERS", "alt-ergo,z3")
    )
    parser.add_argument(
        "--timeout", type=int, default=int(os.environ.get("ACSL_TIMEOUT", "20"))
    )
    parser.add_argument("--wall-timeout", type=int, default=300)
    parser.add_argument("--jobs", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    args = parser.parse_args()

    manifest_path = args.manifest or args.data_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.split == "all":
        selected_ids = [
            task_id for values in manifest["splits"].values() for task_id in values
        ]
        selected_ids = list(dict.fromkeys(selected_ids))
    else:
        selected_ids = list(manifest["splits"][args.split])
    if args.task_id:
        requested = set(args.task_id)
        outside_split = sorted(requested - set(selected_ids))
        if outside_split:
            raise SystemExit(
                f"requested IDs are absent from split {args.split}: {outside_split[:3]}"
            )
        selected_ids = [task_id for task_id in selected_ids if task_id in requested]
    selected_set = set(selected_ids)
    records = [
        record
        for path in sorted(args.data_dir.glob(args.data_glob))
        for record in load_jsonl(path)
    ]
    by_id = {stable_id(record): record for record in records}
    missing = sorted(selected_set - by_id.keys())
    if missing:
        raise SystemExit(
            f"manifest contains {len(missing)} IDs absent from data: {missing[:3]}"
        )

    flags = (
        "-wp",
        "-wp-rte",
        "-wp-prover",
        args.provers,
        "-wp-timeout",
        str(args.timeout),
    )
    policy = {
        "framac_bin": args.framac_bin,
        "flags": list(flags),
        "wall_timeout": args.wall_timeout,
        "jobs": args.jobs,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    existing: dict[str, dict] = {}
    if args.output.exists():
        for row in load_jsonl(args.output):
            if (
                row.get("replay_policy") == policy
                and row.get("stable_id") in selected_set
            ):
                existing[row["stable_id"]] = row

    pending = [by_id[task_id] for task_id in selected_ids if task_id not in existing]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if existing else "w"
    with (
        args.output.open(mode, encoding="utf-8", buffering=1) as stream,
        concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool,
    ):
        futures = {
            pool.submit(
                replay_one,
                record,
                framac_bin=args.framac_bin,
                flags=flags,
                wall_timeout=args.wall_timeout,
            ): stable_id(record)
            for record in pending
        }
        for number, future in enumerate(
            concurrent.futures.as_completed(futures), start=1
        ):
            row = future.result()
            row["replay_policy"] = policy
            existing[row["stable_id"]] = row
            stream.write(json.dumps(row, sort_keys=True) + "\n")
            if number == 1 or number % 10 == 0 or number == len(pending):
                print(f"completed {len(existing)}/{len(selected_ids)}", flush=True)

    summary = summarize(
        selected_ids=selected_ids,
        results=existing,
        policy=policy,
        split=args.split,
    )
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    complete = summary["completed"] == summary["expected"]
    return 0 if complete and summary["fully_proved"] == summary["expected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
