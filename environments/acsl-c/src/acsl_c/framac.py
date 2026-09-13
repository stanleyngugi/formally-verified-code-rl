"""Parse Frama-C/WP verification results into a compact verdict dict.

Primary input: the JSON report written by `-wp-report-json` (Frama-C >= 30).
Each goal record carries: goal, property, function, behavior, line, passed,
verdict, provers[{prover,time,success}], proved, timeout, unknown, failed,
cached, subgoals.

Fallback input: raw stdout containing the documented summary line
"Proved goals: N / M".
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

SUMMARY_RE = re.compile(r"Proved goals:\s*(\d+)\s*/\s*(\d+)")
RESULTS_LINE_RE = re.compile(
    r"verification results::\s*(\d+)\s*verified,\s*(\d+)\s*errors"
)


def _nonnegative_int(value: object) -> bool:
    """Return whether *value* is an integer count rather than a truthy bool."""

    return type(value) is int and value >= 0


@dataclass
class Verdict:
    # Default to failure so incomplete or forward-incompatible reports cannot
    # raise past the reward boundary or accidentally manufacture success.
    ok: bool = False
    parse_ok: bool = False
    compiled: bool = False
    goals_total: int = 0
    goals_proved: int = 0
    rte_total: int = 0
    rte_proved: int = 0
    timeouts: int = 0
    failures: list[dict] = field(default_factory=list)
    crash: str | None = None
    exit_code: int | None = None
    stdout_tail: str = ""
    stderr_tail: str = ""

    @property
    def progress_eligible(self) -> bool:
        """Whether parsed goal counts are safe to expose as partial progress."""

        counts_are_valid = (
            _nonnegative_int(self.goals_total)
            and _nonnegative_int(self.goals_proved)
            and _nonnegative_int(self.rte_total)
            and _nonnegative_int(self.rte_proved)
            and _nonnegative_int(self.timeouts)
            and self.goals_proved <= self.goals_total
            and self.rte_proved <= self.rte_total <= self.goals_total
            and isinstance(self.failures, list)
        )
        exit_is_valid = self.exit_code is None or (
            type(self.exit_code) is int and self.exit_code == 0
        )
        return (
            self.parse_ok is True
            and self.compiled is True
            and counts_are_valid
            and self.goals_total > 0
            and self.crash is None
            and exit_is_valid
        )

    def reconcile_ok(self, *, declared_ok: object | None = None) -> Verdict:
        """Recompute full-proof status from all fail-closed verdict invariants.

        ``declared_ok`` preserves an upstream negative verdict but can never
        turn structurally inconsistent fields into success.
        """

        full_proof = (
            self.progress_eligible
            and self.timeouts == 0
            and self.goals_proved == self.goals_total
            and not self.failures
        )
        self.ok = full_proof and (declared_ok is None or declared_ok is True)
        return self

    @property
    def fraction(self) -> float:
        if not self.progress_eligible:
            return 0.0
        return self.goals_proved / self.goals_total

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "parse_ok": self.parse_ok,
            "compiled": self.compiled,
            "goals_proved": self.goals_proved,
            "goals_total": self.goals_total,
            "rte_proved": self.rte_proved,
            "rte_total": self.rte_total,
            "timeouts": self.timeouts,
            "n_failures": len(self.failures),
            "failures": self.failures,
            "crash": self.crash,
            "exit_code": self.exit_code,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> Verdict:
        fields = {
            "ok",
            "parse_ok",
            "compiled",
            "goals_total",
            "goals_proved",
            "rte_total",
            "rte_proved",
            "timeouts",
            "failures",
            "crash",
            "exit_code",
            "stdout_tail",
            "stderr_tail",
        }
        verdict = cls(
            **{key: value for key, value in payload.items() if key in fields}
        )
        declared_failures = payload.get("n_failures")
        if declared_failures is not None and (
            not _nonnegative_int(declared_failures)
            or not isinstance(verdict.failures, list)
            or declared_failures != len(verdict.failures)
        ):
            verdict.parse_ok = False
        return verdict.reconcile_ok(declared_ok=payload.get("ok") is True)


def from_wp_report_json(payload: str) -> Verdict | None:
    try:
        records = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(records, list):
        return None
    v = Verdict(ok=False, parse_ok=True, compiled=True)
    for rec in records:
        if not isinstance(rec, dict):
            v.parse_ok = False
            continue
        smoke_field = rec.get("smoke", False)
        if not isinstance(smoke_field, bool):
            v.parse_ok = False
        if smoke_field is True:
            continue
        # Frama-C emits a JSON boolean. Do not let malformed strings such as
        # ``"false"`` become truthy and manufacture a proof.
        passed_field = rec.get("passed")
        if not isinstance(passed_field, bool):
            v.parse_ok = False
        passed = passed_field is True
        v.goals_total += 1
        if passed:
            v.goals_proved += 1
        prop = str(rec.get("property", ""))
        if "@rte" in prop.lower() or "rte" in prop.lower():
            v.rte_total += 1
            v.rte_proved += int(passed)
        for p in rec.get("provers", []):
            name = str(p.get("prover", "")).lower()
            if "timeout" in name or "t" == name.strip():
                pass
        timeout_field = rec.get("timeout", 0)
        if not _nonnegative_int(timeout_field):
            v.parse_ok = False
            timeout = 0
        else:
            timeout = timeout_field
        if timeout > 0:
            v.timeouts += timeout
        if not passed and len(v.failures) < 20:
            v.failures.append(
                {
                    "goal": rec.get("goal"),
                    "property": prop,
                    "function": rec.get("function"),
                    "line": rec.get("line"),
                    "verdict": rec.get("verdict"),
                }
            )
    return v.reconcile_ok()


def from_stdout(stdout: str) -> Verdict | None:
    m = SUMMARY_RE.search(stdout or "")
    if m is None:
        return None
    proved, total = int(m.group(1)), int(m.group(2))
    v = Verdict(
        ok=False,
        parse_ok=True,
        compiled="error" not in stdout[:2000].lower(),
        goals_proved=proved,
        goals_total=total,
    )
    return v.reconcile_ok()


def parse(wp_report_json: str | None = None, stdout: str = "") -> Verdict:
    if wp_report_json:
        v = from_wp_report_json(wp_report_json)
        if v is not None:
            return v
    v = from_stdout(stdout)
    if v is not None:
        return v
    return Verdict(ok=False, crash="no parseable frama-c output")


def from_runner_output(stdout: str, *, exit_code: int | None = None) -> Verdict:
    """Parse the final JSON line emitted by :mod:`acsl_c.verify_script`."""
    for line in reversed((stdout or "").splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        if isinstance(payload.get("verdict"), dict):
            verdict = Verdict.from_dict(payload["verdict"])
            reported_exit = payload.get("exit_code")
            # A nonzero outer runner exit cannot be hidden by a nominally
            # successful embedded Frama-C result.
            verdict.exit_code = (
                exit_code
                if exit_code is not None and exit_code != 0
                else reported_exit
            )
            return verdict.reconcile_ok(declared_ok=verdict.ok)
        if payload.get("error"):
            return Verdict(
                ok=False,
                crash=str(payload["error"]),
                exit_code=payload.get("exit_code", exit_code),
                stdout_tail=str(payload.get("stdout_tail", "")),
                stderr_tail=str(payload.get("stderr_tail", "")),
            )
    return Verdict(
        ok=False, crash="no parseable verifier-runner output", exit_code=exit_code
    )
