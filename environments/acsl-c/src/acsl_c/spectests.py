"""Specification-strength scoring (anti-Goodhart component, ADR-004 r4).

The canonical CASP task is fixed-annotation body completion.  For that mode the
strongest possible check is structural: the submitted program must preserve all
annotations and all code outside the target body.  Full specification-synthesis
tasks remain ineligible unless a future negative-spectest executor is supplied.
"""

from __future__ import annotations

from acsl_c.integrity import check_fixed_task_integrity


def spec_strength_score(
    completion: str,
    *,
    mode: str,
    skeleton_c: str | None,
    has_spectests: bool = False,
    spectests: list[dict] | None = None,
    verdict=None,
    missing_spectests_score: float = 0.0,
) -> float:
    if verdict is not None and not verdict.ok:
        return 0.0
    if mode == "hints":
        if not skeleton_c:
            return 0.0
        return check_fixed_task_integrity(completion, skeleton_c).score
    if has_spectests and spectests:
        # A full-mode spectest must carry a clean, recorded executor result.
        # Never trust a bare ``rejected`` flag: an unexecuted or crashed test
        # would otherwise turn missing evidence into specification reward.
        if not all(_is_executed_result(test) for test in spectests):
            return 0.0
        return sum(test["rejected"] for test in spectests) / len(spectests)
    return max(0.0, min(1.0, missing_spectests_score))


def _is_executed_result(test: dict) -> bool:
    """Return whether *test* contains trustworthy executor evidence.

    The executor is deliberately kept outside the online reward path for now,
    but its serialized contract is strict so future ingestion cannot accidentally
    activate unexecuted or infrastructure-failed spectests.
    """

    if not isinstance(test, dict) or test.get("executed") is not True:
        return False
    if not isinstance(test.get("rejected"), bool):
        return False
    verdict = test.get("verdict")
    if not isinstance(verdict, dict):
        return False
    return (
        verdict.get("crash") in (None, "")
        and int(verdict.get("timeouts", 0)) == 0
        and bool(verdict.get("parse_ok"))
        and int(verdict.get("goals_total", 0)) > 0
    )
