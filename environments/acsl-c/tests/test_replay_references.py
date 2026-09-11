import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "replay_references.py"
SPEC = importlib.util.spec_from_file_location("replay_references", SCRIPT)
replay = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(replay)


def test_stable_id_normalizes_newlines():
    unix = {"reference_solution": "int f(void) {\n return 1;\n}\n"}
    windows = {"reference_solution": "int f(void) {\r\n return 1;\r\n}\r\n"}
    assert replay.stable_id(unix) == replay.stable_id(windows)


def test_summary_counts_failures(monkeypatch):
    monkeypatch.setattr(replay, "command_output", lambda command: "version")
    policy = {"framac_bin": "frama-c", "flags": [], "wall_timeout": 30}
    results = {
        "a": {
            "duration_seconds": 1.25,
            "verdict": {
                "ok": True,
                "goals_proved": 3,
                "goals_total": 3,
                "rte_proved": 1,
                "rte_total": 1,
                "timeouts": 0,
            },
        },
        "b": {
            "duration_seconds": 2.0,
            "verdict": {
                "ok": False,
                "parse_ok": True,
                "compiled": True,
                "goals_proved": 1,
                "goals_total": 2,
                "rte_proved": 0,
                "rte_total": 1,
                "timeouts": 1,
            },
        },
    }
    summary = replay.summarize(
        selected_ids=["a", "b", "missing"], results=results, policy=policy, split="all"
    )
    assert summary["expected"] == 3
    assert summary["completed"] == 2
    assert summary["fully_proved"] == 1
    assert summary["goals_proved"] == 4
    assert summary["failure_kinds"] == {"solver_timeout": 1}
    assert json.loads(json.dumps(summary))["tool_versions"]["frama_c"] == "version"
