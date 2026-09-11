from acsl_c.spectests import spec_strength_score


def clean(rejected: bool) -> dict:
    return {
        "executed": True,
        "rejected": rejected,
        "verdict": {
            "parse_ok": True,
            "goals_total": 3,
            "timeouts": 0,
            "crash": None,
        },
    }


def test_unexecuted_spectest_cannot_earn_strength():
    assert (
        spec_strength_score(
            "candidate",
            mode="full",
            skeleton_c=None,
            has_spectests=True,
            spectests=[{"rejected": True}],
        )
        == 0.0
    )


def test_crashed_spectest_cannot_earn_strength():
    failed = clean(True)
    failed["verdict"]["crash"] = "frama-c crashed"
    assert (
        spec_strength_score(
            "candidate",
            mode="full",
            skeleton_c=None,
            has_spectests=True,
            spectests=[failed],
        )
        == 0.0
    )


def test_clean_executed_results_are_averaged():
    assert (
        spec_strength_score(
            "candidate",
            mode="full",
            skeleton_c=None,
            has_spectests=True,
            spectests=[clean(True), clean(False)],
        )
        == 0.5
    )
