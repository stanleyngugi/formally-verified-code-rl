"""ACSL-C environment package.

Pure parsing/integrity helpers remain importable on documentation and Windows
hosts; the complete taskset additionally requires the pinned Linux-only
``verifiers.v1`` stack.
"""

from acsl_c.framac import Verdict, parse

__all__ = ["Verdict", "parse"]

try:
    from acsl_c.taskset import (
        AcslCData,
        AcslCTask,
        AcslCTaskConfig,
        AcslCTaskset,
        AcslCTasksetConfig,
        extract_code,
        load_environment,
        load_taskset,
        stable_record_id,
    )

    __all__ = [
        "AcslCData",
        "AcslCTask",
        "AcslCTaskConfig",
        "AcslCTaskset",
        "AcslCTasksetConfig",
        "Verdict",
        "extract_code",
        "load_environment",
        "load_taskset",
        "parse",
        "stable_record_id",
    ]
except ImportError as exc:
    if getattr(exc, "name", None) not in {
        "verifiers",
        "verifiers.v1",
        "fcntl",
    } and "fcntl" not in str(exc):
        raise
