"""Fail-closed tests for the self-contained in-container verifier runner."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "verify_script",
    Path(__file__).parent.parent / "src" / "acsl_c" / "verify_script.py",
)
verify_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_script)


def record(*, passed=True, timeout=0):
    return {
        "goal": "g1",
        "property": "f@ensures",
        "function": "f",
        "line": 3,
        "smoke": False,
        "passed": passed,
        "verdict": "Valid" if passed else "Unknown",
        "timeout": timeout,
    }


def test_embedded_report_rejects_all_pass_with_timeout():
    verdict = verify_script._from_report([record(timeout=1)])
    assert verdict is not None
    assert verdict["parse_ok"] is True
    assert verdict["goals_proved"] == verdict["goals_total"] == 1
    assert verdict["timeouts"] == 1
    assert verdict["ok"] is False


def test_embedded_report_rejects_negative_timeout_as_malformed():
    verdict = verify_script._from_report([record(timeout=-1)])
    assert verdict is not None
    assert verdict["parse_ok"] is False
    assert verdict["ok"] is False


def test_embedded_report_rejects_noninteger_timeout_and_malformed_records():
    numeric_string = record(timeout="0")
    malformed_smoke = record()
    malformed_smoke["smoke"] = "false"
    verdict = verify_script._from_report(
        [numeric_string, malformed_smoke, "not-a-goal-record"]
    )
    assert verdict is not None
    assert verdict["parse_ok"] is False
    assert verdict["ok"] is False


def test_embedded_stdout_rejects_error_even_with_all_goals_reported_proved():
    verdict = verify_script._from_stdout(
        "[kernel] user error followed by [wp] Proved goals: 2 / 2"
    )
    assert verdict is not None
    assert verdict["compiled"] is False
    assert verdict["ok"] is False


def test_embedded_full_proof_rejects_nonzero_exit_and_failures():
    verdict = {
        "ok": True,
        "parse_ok": True,
        "compiled": True,
        "goals_proved": 2,
        "goals_total": 2,
        "rte_proved": 0,
        "rte_total": 0,
        "timeouts": 0,
        "failures": [],
        "crash": None,
        "exit_code": 1,
    }
    assert verify_script._full_proof_ok(verdict) is False

    verdict["exit_code"] = 0
    verdict["failures"] = [{"goal": "g2", "verdict": "Unknown"}]
    assert verify_script._full_proof_ok(verdict) is False
