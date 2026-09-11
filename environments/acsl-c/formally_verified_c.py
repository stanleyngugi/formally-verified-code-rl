"""Prime Environment Hub entry point for Formally Verified C."""

import verifiers.v1 as vf

from acsl_c import (
    AcslCData,
    AcslCTask,
    AcslCTaskConfig,
    AcslCTaskset,
    AcslCTasksetConfig,
)
from acsl_c import (
    load_environment as _load_environment,
)
from acsl_c import (
    load_taskset as _load_taskset,
)


def load_taskset(config: AcslCTasksetConfig) -> AcslCTaskset:
    """Load the reusable v1 taskset from Prime's resolved config."""
    return _load_taskset(config)


def load_environment(config: vf.EnvConfig) -> vf.Env:
    """Load the standard single-agent v1 environment."""
    return _load_environment(config)


__all__ = [
    "AcslCData",
    "AcslCTask",
    "AcslCTaskConfig",
    "AcslCTaskset",
    "AcslCTasksetConfig",
    "load_environment",
    "load_taskset",
]
