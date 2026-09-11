"""Run a read-only preflight for ACSL-C release and training readiness.

Environment publication does not require the canonical two-GPU asynchronous
trainer topology.  The report therefore exposes independent release and async
training gates. Missing dependencies are structured blockers; the script never
installs packages, starts services, or mutates the repository except for an
explicitly requested JSON output file.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED_SPLITS = {"train": 33, "validation": 15, "test": 16}
EXPECTED_PRIME_COMMIT = "ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1"
EXPECTED_VERIFIERS_COMMIT = "b2e4e8157783b2c0dffc7821044c87f29f1c3ccf"
DEFAULT_IMAGE = "ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc"
ENV_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ENV_ROOT.parents[1]


def _command_check(name: str, *args: str, timeout: int = 20) -> dict:
    path = shutil.which(name)
    result = {"command": name, "path": path, "available": path is not None}
    if path is None:
        return result
    try:
        completed = subprocess.run(
            [path, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result
    result["returncode"] = completed.returncode
    output = (completed.stdout or completed.stderr).strip()
    if output:
        result["output"] = output[-1000:]
    result["healthy"] = completed.returncode == 0
    return result


def _split_check(manifest_path: Path) -> dict:
    if not manifest_path.is_file():
        return {"path": str(manifest_path), "present": False}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        splits = manifest["splits"]
        counts = {name: len(splits.get(name, [])) for name in EXPECTED_SPLITS}
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return {
            "path": str(manifest_path),
            "present": True,
            "valid": False,
            "error": f"{type(exc).__name__}: {exc}",
        }
    return {
        "path": str(manifest_path),
        "present": True,
        "valid": counts == EXPECTED_SPLITS,
        "counts": counts,
        "expected": EXPECTED_SPLITS,
    }


def _docker_check(*args: str, timeout: int = 20) -> dict:
    direct = _command_check("docker", *args, timeout=timeout)
    if direct.get("healthy"):
        direct["via_sudo"] = False
        return direct
    elevated = _command_check("sudo", "-n", "docker", *args, timeout=timeout)
    if elevated.get("healthy"):
        elevated["command"] = "sudo -n docker"
        elevated["via_sudo"] = True
        return elevated
    direct["sudo_fallback"] = elevated
    return direct


def _git_head(path: Path) -> dict:
    check = _command_check("git", "-C", str(path), "rev-parse", "HEAD")
    check["commit"] = check.get("output") if check.get("healthy") else None
    return check


def _gpu_check() -> dict:
    check = _command_check("nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader", timeout=15)
    output = check.get("output", "") if check.get("healthy") else ""
    count = len([line for line in output.splitlines() if line.strip()])
    check["count"] = count
    check["canonical_two_gpu_topology"] = count >= 2
    return check


def build_report(*, prime_root: Path | None = None, image: str = DEFAULT_IMAGE) -> dict:
    manifest = _split_check(ENV_ROOT / "data" / "packs" / "core-v1" / "manifest.json")
    python_ok = sys.version_info[:2] in {(3, 11), (3, 12), (3, 13)}
    checks = {
        "python": {
            "version": platform.python_version(),
            "supported": python_ok,
        },
        "splits": manifest,
        "frama_c": _command_check("frama-c", "-version"),
        "alt_ergo": _command_check("alt-ergo", "--version"),
        "z3": _command_check("z3", "--version"),
        "docker": _docker_check("info", timeout=15),
        "judge_image": _docker_check("image", "inspect", image, timeout=30),
        "gpu": _gpu_check(),
    }
    prime_path = prime_root or (Path(str(Path.cwd())) if (Path.cwd() / "pyproject.toml").is_file() else None)
    if prime_path is not None:
        prime_head = _git_head(prime_path)
        verifiers_path = prime_path / "deps" / "verifiers"
        verifiers_head = _git_head(verifiers_path)
        checks["prime_rl"] = {
            "path": str(prime_path),
            "checkout_present": (prime_path / "pyproject.toml").is_file(),
            "git": prime_head,
            "commit_matches": prime_head.get("commit") == EXPECTED_PRIME_COMMIT,
            "verifiers_git": verifiers_head,
            "verifiers_commit_matches": (verifiers_head.get("commit") == EXPECTED_VERIFIERS_COMMIT),
            "rl_installed": (prime_path / ".venv" / "bin" / "rl").is_file()
            or (prime_path / ".venv" / "Scripts" / "rl.exe").is_file(),
        }
    else:
        checks["prime_rl"] = {"checkout_present": False, "path": None}

    local_ready = (
        checks["python"]["supported"]
        and checks["splits"].get("valid", False)
        and checks["frama_c"].get("healthy", False)
        and checks["alt_ergo"].get("healthy", False)
        and checks["z3"].get("healthy", False)
    )
    container_judge_ready = checks["docker"].get("healthy", False) and checks["judge_image"].get("healthy", False)
    prime_stack_ready = all(
        checks["prime_rl"].get(key, False)
        for key in (
            "checkout_present",
            "commit_matches",
            "verifiers_commit_matches",
            "rl_installed",
        )
    )
    gpu_topology_ready = checks["gpu"]["canonical_two_gpu_topology"]
    # A publishable environment needs deterministic data, the portable judge,
    # and the pinned hub/runtime integration. A native Frama-C install is a
    # useful developer path, but the container is the release boundary.
    environment_release_ready = (
        checks["python"]["supported"]
        and checks["splits"].get("valid", False)
        and container_judge_ready
        and prime_stack_ready
    )
    async_training_ready = environment_release_ready and gpu_topology_ready
    return {
        "schema": "acsl-c-preflight-v3",
        "repository": str(REPO_ROOT),
        "local_judge_ready": local_ready,
        "container_judge_ready": container_judge_ready,
        "prime_stack_ready": prime_stack_ready,
        "gpu_topology_ready": gpu_topology_ready,
        "environment_release_ready": environment_release_ready,
        "async_training_ready": async_training_ready,
        # Backward-compatible name for callers that used v2. In v3 it means
        # the canonical async topology, not environment publication readiness.
        "production_ready": async_training_ready,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prime-root",
        type=Path,
        help="Prime-RL checkout to inspect (defaults to the current directory when applicable)",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--output", type=Path, help="also write the JSON report here")
    parser.add_argument(
        "--require",
        choices=("release", "async", "none"),
        default="release",
        help=(
            "readiness gate controlling the exit status (default: release; "
            "async additionally requires at least two locally visible GPUs)"
        ),
    )
    args = parser.parse_args()
    report = build_report(prime_root=args.prime_root, image=args.image)
    encoded = json.dumps(report, indent=2)
    print(encoded)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    if args.require == "none":
        return 0
    required_key = {
        "release": "environment_release_ready",
        "async": "async_training_ready",
    }[args.require]
    return 0 if report[required_key] else 2


if __name__ == "__main__":
    raise SystemExit(main())
