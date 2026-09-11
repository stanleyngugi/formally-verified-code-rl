#!/usr/bin/env python3
"""Debug-only real Frama-C smoke through Verifiers' subprocess runtime.

Production runs must use Docker/Prime isolation. Run this only with trusted
reference data on a development machine with the pinned toolchain in PATH.
"""

import asyncio
import time
from pathlib import Path
from types import SimpleNamespace

from verifiers.v1.runtimes import SubprocessConfig, SubprocessRuntime

from acsl_c.taskset import AcslCTaskset, AcslCTasksetConfig

ROOT = Path(__file__).parent.parent


async def component_scores(task, source, runtime):
    trace = SimpleNamespace(last_reply=source, info={})
    values = (
        await task.acsl_gate(trace, runtime),
        await task.acsl_vc_fraction(trace, runtime),
        await task.acsl_full_proof(trace, runtime),
        await task.acsl_spec_strength(trace, runtime),
    )
    return values, trace.info


async def main() -> int:
    config = AcslCTasksetConfig(data_dir=str(ROOT / "data"), split="test", max_tasks=1)
    target = next(iter(AcslCTaskset(config).load()))
    runtime = SubprocessRuntime(
        SubprocessConfig(), name=f"acslc_live_smoke_{int(time.time())}"
    )
    await runtime.start()
    try:
        good, info = await component_scores(
            target, target.data.reference_solution, runtime
        )
        tampered = target.data.reference_solution.replace("ensures", "ensures 0 &&", 1)
        assert tampered != target.data.reference_solution
        bad, bad_info = await component_scores(target, tampered, runtime)
    finally:
        await runtime.teardown()

    print("REFERENCE", good, info)
    print("ANNOTATION_TAMPER", bad, bad_info)
    ok = good == (1.0, 1.0, 1.0, 1.0) and bad == (0.0, 0.0, 0.0, 0.0)
    print("LIVE_FRAMAC_SMOKE_OK" if ok else "LIVE_FRAMAC_SMOKE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
