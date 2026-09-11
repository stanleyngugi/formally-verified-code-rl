from acsl_c.cache import VerdictCache, verification_key
from acsl_c.framac import Verdict


def test_cache_roundtrip(tmp_path):
    cache = VerdictCache(tmp_path / "verdicts.sqlite3")
    key = verification_key(
        "int f(void){return 0;}",
        toolchain_id="test-toolchain",
        provers="z3",
        timeout=1,
    )
    verdict = Verdict(
        ok=False,
        parse_ok=True,
        compiled=True,
        goals_total=2,
        goals_proved=1,
        failures=[{"goal": "g2", "verdict": "unknown"}],
    )
    assert cache.get(key) is None
    cache.put(key, verdict)
    restored = cache.get(key)
    assert restored is not None
    assert restored.to_dict() == verdict.to_dict()


def test_cache_key_includes_judge_configuration():
    base = {"source": "x", "toolchain_id": "t", "provers": "z3", "timeout": 1}
    first = verification_key(**base)
    assert first != verification_key(**{**base, "timeout": 2})
    assert first != verification_key(**{**base, "toolchain_id": "other"})
    assert first != verification_key(**{**base, "runner_id": "changed"})
