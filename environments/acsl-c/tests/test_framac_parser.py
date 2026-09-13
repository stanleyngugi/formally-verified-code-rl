"""Unit tests for acsl_c.framac parser against fixture WP reports.

Loads framac.py directly by path: importing the acsl_c package pulls in
verifiers.v1, which requires Unix (fcntl) and is meant to run in WSL/Linux.
"""

import importlib.util
import json
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "framac",
    Path(__file__).parent.parent / "src" / "acsl_c" / "framac.py",
)
framac = importlib.util.module_from_spec(_spec)
sys.modules["framac"] = framac
_spec.loader.exec_module(framac)


def goal(gid, prop, passed, fn="f", line=3, timeout=0):
    return {
        "goal": gid,
        "property": prop,
        "file": "/tmp/solution.c",
        "line": line,
        "function": fn,
        "smoke": False,
        "passed": passed,
        "verdict": "Valid" if passed else "Unknown",
        "provers": [{"prover": "Alt-Ergo", "time": 0.01, "success": int(passed)}],
        "proved": 1 if passed else 0,
        "timeout": timeout,
        "unknown": 0 if passed else 1,
        "failed": 0,
    }


ALL_PASS = json.dumps(
    [
        goal("g1", "f@requires", True),
        goal("g2", "f@ensures", True),
        goal("g3", "rte@div_by_zero", True),
    ]
)

PARTIAL = json.dumps(
    [
        goal("g1", "f@requires", True),
        goal("g2", "f@invariant", False, line=7),
        goal("g3", "f@assert", False, line=9, timeout=1),
    ]
)

SMOKE_ONLY = json.dumps([dict(goal("s1", "x@prop", True), smoke=True)])


def test_all_pass():
    v = framac.from_wp_report_json(ALL_PASS)
    assert v is not None and v.parse_ok and v.ok
    assert (v.goals_proved, v.goals_total) == (3, 3)
    assert v.rte_proved == 1 and v.rte_total == 1
    assert v.fraction == 1.0
    assert not v.failures


def test_partial_pass():
    v = framac.from_wp_report_json(PARTIAL)
    assert v is not None and not v.ok
    assert (v.goals_proved, v.goals_total) == (1, 3)
    assert v.timeouts == 1
    assert len(v.failures) == 2
    lines = {f["line"] for f in v.failures}
    assert lines == {7, 9}


def test_smoke_excluded():
    v = framac.from_wp_report_json(SMOKE_ONLY)
    assert v is not None and v.goals_total == 0 and not v.ok


def test_malformed_falls_back_to_stdout():
    v = framac.parse(wp_report_json="not json{", stdout="... [wp] Proved goals: 4 / 6")
    assert v.parse_ok and (v.goals_proved, v.goals_total) == (4, 6)
    assert not v.ok


def test_no_output_is_crash_not_exception():
    v = framac.parse(stdout="")
    assert v.crash is not None and not v.ok and v.goals_total == 0


def test_empty_report_counts_as_not_ok():
    v = framac.from_wp_report_json(json.dumps([]))
    assert v is not None and v.goals_total == 0 and not v.ok


def test_malformed_truthy_pass_field_cannot_manufacture_proof():
    malformed = goal("g1", "f@ensures", False)
    malformed["passed"] = "false"
    report = json.dumps([malformed])
    v = framac.from_wp_report_json(report)
    assert v is not None and not v.ok and not v.parse_ok
    assert v.goals_proved == 0


def test_malformed_timeout_fails_closed():
    record = goal("g1", "f@ensures", True)
    record["timeout"] = "not-a-number"
    v = framac.from_wp_report_json(json.dumps([record]))
    assert v is not None and not v.ok and not v.parse_ok


def test_all_pass_with_timeout_cannot_be_full_proof():
    record = goal("g1", "f@ensures", True, timeout=1)
    v = framac.from_wp_report_json(json.dumps([record]))
    assert v is not None and v.parse_ok and v.compiled
    assert v.goals_proved == v.goals_total == 1
    assert v.timeouts == 1 and not v.ok


def test_negative_timeout_is_malformed_and_fails_closed():
    record = goal("g1", "f@ensures", True, timeout=-1)
    v = framac.from_wp_report_json(json.dumps([record]))
    assert v is not None and not v.parse_ok and not v.ok


def test_noninteger_timeout_and_malformed_record_fail_closed():
    numeric_string = goal("g1", "f@ensures", True)
    numeric_string["timeout"] = "0"
    malformed_smoke = goal("g2", "f@ensures", True)
    malformed_smoke["smoke"] = "false"
    v = framac.from_wp_report_json(
        json.dumps([numeric_string, malformed_smoke, "not-a-goal-record"])
    )
    assert v is not None and not v.parse_ok and not v.ok


def test_runner_output_roundtrip():
    payload = {
        "exit_code": 0,
        "verdict": {
            "ok": True,
            "parse_ok": True,
            "compiled": True,
            "goals_proved": 2,
            "goals_total": 2,
            "failures": [],
        },
    }
    v = framac.from_runner_output("noise\n" + json.dumps(payload))
    assert v.ok and v.goals_total == 2 and v.exit_code == 0


def test_runner_output_rejects_declared_success_when_not_compiled():
    payload = {
        "exit_code": 0,
        "verdict": {
            "ok": True,
            "parse_ok": True,
            "compiled": False,
            "goals_proved": 2,
            "goals_total": 2,
            "failures": [],
        },
    }
    v = framac.from_runner_output(json.dumps(payload))
    assert not v.ok and not v.progress_eligible and v.fraction == 0.0


def test_runner_output_rejects_nonzero_embedded_exit():
    payload = {
        "exit_code": 3,
        "verdict": {
            "ok": True,
            "parse_ok": True,
            "compiled": True,
            "goals_proved": 2,
            "goals_total": 2,
            "failures": [],
        },
    }
    v = framac.from_runner_output(json.dumps(payload), exit_code=0)
    assert v.exit_code == 3 and not v.ok and not v.progress_eligible


def test_runner_output_rejects_nonzero_outer_exit():
    payload = {
        "exit_code": 0,
        "verdict": {
            "ok": True,
            "parse_ok": True,
            "compiled": True,
            "goals_proved": 2,
            "goals_total": 2,
            "failures": [],
        },
    }
    v = framac.from_runner_output(json.dumps(payload), exit_code=9)
    assert v.exit_code == 9 and not v.ok and not v.progress_eligible


def test_runner_output_rejects_inconsistent_counts_and_failures():
    bad_counts = {
        "ok": True,
        "parse_ok": True,
        "compiled": True,
        "goals_proved": 3,
        "goals_total": 2,
        "failures": [],
    }
    v = framac.from_runner_output(
        json.dumps({"exit_code": 0, "verdict": bad_counts})
    )
    assert not v.ok and not v.progress_eligible and v.fraction == 0.0

    contradictory_failure = {
        **bad_counts,
        "goals_proved": 2,
        "failures": [{"goal": "g2", "verdict": "Unknown"}],
    }
    v = framac.from_runner_output(
        json.dumps({"exit_code": 0, "verdict": contradictory_failure})
    )
    assert not v.ok


def test_runner_output_requires_explicit_boolean_success():
    verdict = {
        "parse_ok": True,
        "compiled": True,
        "goals_proved": 2,
        "goals_total": 2,
        "failures": [],
    }
    missing = framac.from_runner_output(
        json.dumps({"exit_code": 0, "verdict": verdict})
    )
    verdict["ok"] = "true"
    malformed = framac.from_runner_output(
        json.dumps({"exit_code": 0, "verdict": verdict})
    )
    assert not missing.ok and not malformed.ok


def test_runner_output_rejects_inconsistent_failure_count():
    verdict = {
        "ok": True,
        "parse_ok": True,
        "compiled": True,
        "goals_proved": 2,
        "goals_total": 2,
        "n_failures": 1,
        "failures": [],
    }
    parsed = framac.from_runner_output(
        json.dumps({"exit_code": 0, "verdict": verdict})
    )
    assert not parsed.parse_ok and not parsed.ok


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except AssertionError as e:
                fails += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if fails else 0)
