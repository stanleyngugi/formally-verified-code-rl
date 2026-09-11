# Prime-RL v0.9.0 bootstrap note

This repository targets Prime-RL tag `v0.9.0` (annotated tag object
`834dc327460e22fbb6515d4bf4fe1b8eeeabbb88`, peeled commit
`ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1`) paired with the vendored Verifiers
commit `b2e4e8157783b2c0dffc7821044c87f29f1c3ccf`. Prime's upstream manual
setup requires Python 3.12, initialized submodules, and `uv sync --all-extras`
followed by `uv sync --all-extras --all-packages` for a custom environment.

The upstream v0.9.0 package is not available as a normal PyPI release in the
observed resolver. A direct `uv run --with git+...` attempt also spent several
minutes resolving/building its large GPU dependency graph and was interrupted;
that is an infrastructure timeout, not evidence that the environment or model
is incompatible. The repository therefore does not claim that `rl` has run.

## Reproducible Linux procedure

Run on Python 3.12 with a Docker daemon and at least two visible GPUs for the
canonical split train/infer topology:

```bash
git clone --branch v0.9.0 https://github.com/PrimeIntellect-ai/prime-rl.git
cd prime-rl
git submodule update --init -- deps/verifiers deps/renderers deps/prime-envs deps/pydantic-config
uv sync --all-extras --all-packages
uv run rl @ /workspace/verified-rl-envs/environments/acsl-c/configs/train.toml --dry-run
```

Before training, copy this environment into the Prime workspace (or install it
as the workspace member), build `environments/acsl-c/docker/Dockerfile`, and
record the immutable image digest. Then run the repository's preflight gates:

1. reference replay in the image, including parse/compile/WP+RTE statistics;
2. executed negative spectest generation and independent label audit;
3. `rl --dry-run`, followed by a one- or two-step canary and checkpoint resume;
4. only then the three-seed 500-step experiment from `EXPERIMENT_PROTOCOL.md`.

Prime's own documentation confirms that the full `rl` topology is an
inference + orchestrator + trainer path and calls for two GPUs in its
end-to-end example. A single managed T4 is useful for model and prompt probes,
but cannot be substituted for that run.

## Session 2026-09-10 — core CLI gate

The exact Prime-RL checkout was materialized successfully with the core
package scope (GPU extras intentionally omitted while no GPU host is
available):

```text
uv sync --package prime-rl --no-default-groups
Installed 156 packages
prime-rl==0.9.0
verifiers==0.3.1
Python 3.12.3
```

The full `--all-extras --all-packages` attempt was not used as the project
gate because an unrelated `tau2-bench` Git fetch failed with an HTTP early-EOF
pack error. The core install is sufficient for config validation and avoids
claiming that every optional Prime workspace environment was installed.

The local `acsl-c` package was installed into the Prime venv without changing
its dependencies, and the exact workspace link was created:

```text
/workspace/acsl-c -> /mnt/c/Users/stanley/Desktop/verified-rl-envs/environments/acsl-c
```

Prime-RL's dry-run passed against the repository configuration:

```text
rl @ /workspace/acsl-c/configs/train.toml \
  --dry-run True --dashboard False \
  --output-dir /tmp/acslc-prime-dry --run.name acslc-dry
```

It wrote resolved `trainer.json`, `inference.json`, and `orchestrator.json`
and exited successfully before model download or training. The resolved
configuration confirms Qwen/Qwen2.5-Coder-7B-Instruct, 2,048-token sequences,
GRPO, the pinned ACSL toolchain identifier, and the train split manifest.
This establishes the software/configuration gate; GPU topology, model
loading, canary, checkpoint resume, and claim-bearing training remain pending.
