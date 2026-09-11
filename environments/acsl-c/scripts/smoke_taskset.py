#!/usr/bin/env python3
"""Fast taskset/API smoke test; does not invoke Frama-C."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from acsl_c.taskset import AcslCTaskConfig, AcslCTaskset, AcslCTasksetConfig

ROOT = Path(__file__).parent.parent


class FakeRuntime:
    async def write(self, path, data):
        pass

    async def run(self, argv, env):
        if argv[:2] == ["rm", "-f"]:
            return SimpleNamespace(stdout="", stderr="", exit_code=0)
        verdict = {
            "ok": True,
            "parse_ok": True,
            "goals_proved": 7,
            "goals_total": 7,
            "timeouts": 0,
            "failures": [],
            "crash": None,
        }
        return SimpleNamespace(
            stdout=json.dumps({"verdict": verdict, "exit_code": 0}) + "\n",
            stderr="",
            exit_code=0,
        )


async def main() -> None:
    config = AcslCTasksetConfig(
        data_dir=str(ROOT / "data"),
        split="train",
        max_tasks=5,
        seed=20260909,
        task=AcslCTaskConfig(cache_path=""),
    )
    tasks = list(AcslCTaskset(config).load())
    assert len(tasks) == 5
    task = tasks[0]
    trace = SimpleNamespace(last_reply=task.data.reference_solution, info={})
    runtime = FakeRuntime()
    values = (
        await task.acsl_gate(trace, runtime),
        await task.acsl_vc_fraction(trace, runtime),
        await task.acsl_full_proof(trace, runtime),
        await task.acsl_spec_strength(trace, runtime),
    )
    print("components", values, trace.info)
    assert values == (1.0, 1.0, 1.0, 1.0)
    print(f"TASKSET_SMOKE_OK loaded={len(tasks)} reward={values}")


if __name__ == "__main__":
    asyncio.run(main())
