#!/usr/bin/env python3
"""Run one reference solution through Verifiers v1's Docker runtime.

This is the smallest end-to-end check of the release boundary: taskset plugin
loading, runtime provisioning, the embedded verifier runner, and the pinned
Frama-C image. It intentionally performs no model inference.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from verifiers.v1.runtimes import DockerConfig, DockerRuntime

from acsl_c.taskset import AcslCTaskConfig, AcslCTaskset, AcslCTasksetConfig

ROOT = Path(__file__).resolve().parent.parent


async def run(image: str, split: str) -> dict:
    taskset = AcslCTaskset(
        AcslCTasksetConfig(
            data_dir=str(ROOT / "data"),
            split=split,
            max_tasks=1,
            task=AcslCTaskConfig(cache_path=""),
        )
    )
    task = next(iter(taskset.load()))
    runtime = DockerRuntime(
        DockerConfig(
            image=image,
            workdir="/workspace",
            allow=[],
            cpu=2,
            memory=4,
        ),
        name=f"acslc-docker-smoke-{int(time.time())}",
    )
    await runtime.start()
    try:
        await runtime.prepare_execution([])
        host_escape = await runtime.run(["test", "-e", "/mnt/c/Users/stanley/Desktop/verified-rl-envs"], {})
        network_escape = await runtime.run(
            [
                "python3",
                "-c",
                ("import socket; socket.create_connection(('1.1.1.1', 80), timeout=2)"),
            ],
            {},
        )
        verdict = await task._run_source(task.data.reference_solution or "", runtime)
    finally:
        await runtime.stop()
    return {
        "schema": "acsl-c-docker-smoke-v1",
        "image": image,
        "split": split,
        "task": task.data.stable_id,
        "isolation": {
            "host_workspace_absent": host_escape.exit_code != 0,
            "direct_network_blocked": network_escape.exit_code != 0,
        },
        "verdict": verdict.to_dict(),
        "passed": (verdict.ok and host_escape.exit_code != 0 and network_escape.exit_code != 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--image",
        default="ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593",
    )
    parser.add_argument("--split", default="validation")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = asyncio.run(run(args.image, args.split))
    encoded = json.dumps(result, indent=2)
    print(encoded)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
