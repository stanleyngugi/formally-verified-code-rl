import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import preflight
from preflight import EXPECTED_SPLITS, _split_check, build_report


def test_split_check_reports_expected_counts(tmp_path):
    path = tmp_path / "split_manifest.json"
    path.write_text(
        json.dumps(
            {
                "splits": {
                    name: list(range(count)) for name, count in EXPECTED_SPLITS.items()
                }
            }
        ),
        encoding="utf-8",
    )
    report = _split_check(path)
    assert report["valid"] is True
    assert report["counts"] == EXPECTED_SPLITS


def test_split_check_missing_file_is_structured(tmp_path):
    report = _split_check(tmp_path / "missing.json")
    assert report == {"path": str(tmp_path / "missing.json"), "present": False}


def _healthy_checks(monkeypatch, *, docker=True, gpu_count=0):
    def command(name, *args, **kwargs):
        return {"command": name, "healthy": True, "available": True}

    monkeypatch.setattr(preflight, "_command_check", command)
    monkeypatch.setattr(
        preflight,
        "_docker_check",
        lambda *args, **kwargs: {"healthy": docker, "available": docker},
    )
    monkeypatch.setattr(
        preflight,
        "_gpu_check",
        lambda: {
            "healthy": gpu_count > 0,
            "count": gpu_count,
            "canonical_two_gpu_topology": gpu_count >= 2,
        },
    )


def test_release_readiness_does_not_require_two_gpus(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='prime-rl'\n")
    (tmp_path / "deps" / "verifiers").mkdir(parents=True)
    cli = tmp_path / ".venv" / "bin" / "rl"
    cli.parent.mkdir(parents=True)
    cli.write_text("")
    _healthy_checks(monkeypatch, docker=True, gpu_count=0)
    monkeypatch.setattr(
        preflight,
        "_git_head",
        lambda path: {
            "healthy": True,
            "commit": (
                preflight.EXPECTED_VERIFIERS_COMMIT
                if path.name == "verifiers"
                else preflight.EXPECTED_PRIME_COMMIT
            ),
        },
    )

    report = build_report(prime_root=tmp_path)
    assert report["environment_release_ready"] is True
    assert report["async_training_ready"] is False
    assert report["production_ready"] is False


def test_release_readiness_requires_container_judge(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='prime-rl'\n")
    (tmp_path / "deps" / "verifiers").mkdir(parents=True)
    cli = tmp_path / ".venv" / "bin" / "rl"
    cli.parent.mkdir(parents=True)
    cli.write_text("")
    _healthy_checks(monkeypatch, docker=False, gpu_count=2)
    monkeypatch.setattr(
        preflight,
        "_git_head",
        lambda path: {
            "healthy": True,
            "commit": (
                preflight.EXPECTED_VERIFIERS_COMMIT
                if path.name == "verifiers"
                else preflight.EXPECTED_PRIME_COMMIT
            ),
        },
    )

    report = build_report(prime_root=tmp_path)
    assert report["environment_release_ready"] is False
    assert report["async_training_ready"] is False


def test_prime_stack_requires_exact_commits_and_installed_cli(tmp_path, monkeypatch):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='prime-rl'\n")
    (tmp_path / "deps" / "verifiers").mkdir(parents=True)
    cli = tmp_path / ".venv" / "bin" / "rl"
    cli.parent.mkdir(parents=True)
    cli.write_text("")

    commits = {
        str(tmp_path): preflight.EXPECTED_PRIME_COMMIT,
        str(tmp_path / "deps" / "verifiers"): preflight.EXPECTED_VERIFIERS_COMMIT,
    }
    monkeypatch.setattr(
        preflight,
        "_git_head",
        lambda path: {"healthy": True, "commit": commits[str(path)]},
    )
    report = build_report(prime_root=tmp_path)
    assert report["prime_stack_ready"] is True

    commits[str(tmp_path / "deps" / "verifiers")] = "wrong"
    report = build_report(prime_root=tmp_path)
    assert report["prime_stack_ready"] is False
