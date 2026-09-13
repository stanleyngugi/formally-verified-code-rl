"""Self-contained PEP-723 verifier runner executed inside a rollout runtime.

It accepts one base64-encoded C source argument and emits one compact JSON line.
The script deliberately has no package dependencies so the heavy verifier stack
exists only in the selected subprocess/Docker/remote runtime.

# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

FRAMAC = os.environ.get("FRAMAC_BIN", "frama-c")
PROVERS = os.environ.get("ACSL_PROVERS", "alt-ergo,z3")
TIMEOUT = int(os.environ.get("ACSL_TIMEOUT", "20"))
SUMMARY_RE = re.compile(r"Proved goals:\s*(\d+)\s*/\s*(\d+)")


def _nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _progress_eligible(verdict: dict) -> bool:
    counts_are_valid = (
        _nonnegative_int(verdict.get("goals_total"))
        and _nonnegative_int(verdict.get("goals_proved"))
        and _nonnegative_int(verdict.get("rte_total"))
        and _nonnegative_int(verdict.get("rte_proved"))
        and _nonnegative_int(verdict.get("timeouts"))
        and verdict["goals_proved"] <= verdict["goals_total"]
        and verdict["rte_proved"] <= verdict["rte_total"] <= verdict["goals_total"]
        and isinstance(verdict.get("failures"), list)
    )
    exit_code = verdict.get("exit_code")
    exit_is_valid = exit_code is None or (
        type(exit_code) is int and exit_code == 0
    )
    return (
        verdict.get("parse_ok") is True
        and verdict.get("compiled") is True
        and counts_are_valid
        and verdict["goals_total"] > 0
        and verdict.get("crash") is None
        and exit_is_valid
    )


def _full_proof_ok(verdict: dict) -> bool:
    return (
        _progress_eligible(verdict)
        and verdict["timeouts"] == 0
        and verdict["goals_proved"] == verdict["goals_total"]
        and not verdict["failures"]
    )


def _from_report(records: object) -> dict | None:
    if not isinstance(records, list):
        return None
    verdict = {
        "ok": False,
        "parse_ok": True,
        "compiled": True,
        "goals_total": 0,
        "goals_proved": 0,
        "rte_total": 0,
        "rte_proved": 0,
        "timeouts": 0,
        "failures": [],
        "crash": None,
    }
    for record in records:
        if not isinstance(record, dict):
            verdict["parse_ok"] = False
            continue
        smoke_field = record.get("smoke", False)
        if not isinstance(smoke_field, bool):
            verdict["parse_ok"] = False
        if smoke_field is True:
            continue
        passed_field = record.get("passed")
        if not isinstance(passed_field, bool):
            verdict["parse_ok"] = False
        # Never let a non-empty string such as "false" count as proof.
        passed = passed_field is True
        verdict["goals_total"] += 1
        verdict["goals_proved"] += int(passed)
        prop = str(record.get("property", ""))
        if "rte" in prop.lower():
            verdict["rte_total"] += 1
            verdict["rte_proved"] += int(passed)
        timeout_field = record.get("timeout", 0)
        if not _nonnegative_int(timeout_field):
            verdict["parse_ok"] = False
            timeout = 0
        else:
            timeout = timeout_field
        verdict["timeouts"] += timeout
        if not passed and len(verdict["failures"]) < 20:
            verdict["failures"].append(
                {
                    "goal": record.get("goal"),
                    "property": prop,
                    "function": record.get("function"),
                    "line": record.get("line"),
                    "verdict": record.get("verdict"),
                }
            )
    verdict["ok"] = _full_proof_ok(verdict)
    return verdict


def _from_stdout(stdout: str) -> dict | None:
    match = SUMMARY_RE.search(stdout)
    if match is None:
        return None
    proved, total = int(match.group(1)), int(match.group(2))
    verdict = {
        "ok": False,
        "parse_ok": True,
        "compiled": "error" not in stdout[:2000].lower(),
        "goals_total": total,
        "goals_proved": proved,
        "rte_total": 0,
        "rte_proved": 0,
        "timeouts": 0,
        "failures": [],
        "crash": None,
    }
    verdict["ok"] = _full_proof_ok(verdict)
    return verdict


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "expected exactly one base64 source argument"}))
        return 2
    try:
        source = base64.b64decode(sys.argv[1], validate=True).decode(
            "utf-8", errors="replace"
        )
    except (binascii.Error, UnicodeError, ValueError) as exc:
        print(json.dumps({"error": f"invalid source argument: {exc}"}))
        return 2

    with tempfile.TemporaryDirectory(prefix="acslc_") as tmp:
        cpath = Path(tmp) / "solution.c"
        report = Path(tmp) / "wp-report.json"
        cpath.write_text(source, encoding="utf-8")
        command = [
            FRAMAC,
            "-wp",
            "-wp-rte",
            "-wp-cache",
            "none",
            "-wp-prover",
            PROVERS,
            "-wp-timeout",
            str(TIMEOUT),
            "-wp-report-json",
            str(report),
            str(cpath),
        ]
        try:
            process = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=TIMEOUT * 12 + 60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(json.dumps({"error": "frama-c wall-clock timeout"}))
            return 1
        except FileNotFoundError:
            print(json.dumps({"error": f"{FRAMAC} not found in runtime"}))
            return 3
        except (OSError, subprocess.SubprocessError) as exc:
            print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}))
            return 1

        stdout_tail = process.stdout[-4000:]
        stderr_tail = process.stderr[-2000:]
        verdict = None
        if report.exists():
            try:
                verdict = _from_report(json.loads(report.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
                verdict = None
        verdict = verdict or _from_stdout(process.stdout)
        if verdict is None:
            verdict = {
                "ok": False,
                "parse_ok": False,
                "compiled": False,
                "goals_total": 0,
                "goals_proved": 0,
                "rte_total": 0,
                "rte_proved": 0,
                "timeouts": 0,
                "failures": [],
                "crash": "no parseable frama-c output",
            }
        verdict.update(
            {
                "exit_code": process.returncode,
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
            }
        )
        # Preserve any earlier negative decision and reject a nominally
        # all-passed report when process state contradicts proof success.
        verdict["ok"] = verdict.get("ok") is True and _full_proof_ok(verdict)
        print(json.dumps({"exit_code": process.returncode, "verdict": verdict}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
