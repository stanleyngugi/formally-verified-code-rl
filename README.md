# Formally Verified Code RL

RL environments where models learn to write code that can be **formally proved
correct**, not merely code that passes a test suite. The first environment,
**Formally Verified C**, uses C contracts (ACSL), Frama-C, and
[Prime Intellect Verifiers v1](https://github.com/PrimeIntellect-ai/verifiers).

## The idea

Standard code-RL uses unit tests as the judge. Tests are samples of behavior; a prover is a
proof. For language subsets that have sound automated judges (C/ACSL via Frama-C WP,
Rust via Verus), we replace the test harness with a verifier harness:

```
model completes a C implementation under a fixed ACSL contract
  -> sandboxed Frama-C/WP+RTE discharges proof obligations to SMT solvers
  -> staged reward: parse gate -> % VCs discharged -> full proof -> spec strength
  -> failed proof obligations and verifier diagnostics returned as feedback
```

The result: a reusable signal for training models to write code deductively verified
against its contract across the verifier's modeled input domain, rather than only
code that passes sampled tests.

## Status

| Phase | Language | Judge | State |
|---|---|---|---|
| 1 | C + ACSL | Frama-C WP+RTE (pinned) | Formally Verified C v0.1 technical and public-data gates complete; publication in progress |
| 2 | Rust | Verus (pinned) | planned |
| 3 | Dafny | Dafny/Z3 | planned |

Formally Verified C v0.1 bundles an Apache-2.0, project-authored Core-v1 of 64
family-isolated tasks. All 64 references prove (296/296 obligations, including
84/84 runtime-safety obligations), and all 64 deliberately wrong programs fail
the deterministic negative gate. The public wheel contains no CASP-derived
task payload. CASP remains an explicit research adapter pending record-level
license clearance. See
[docs/PUBLICATION_STRATEGY.md](docs/PUBLICATION_STRATEGY.md),
[docs/RELATED_WORK.md](docs/RELATED_WORK.md),
[docs/ACSL_SOURCE_LICENSE_AUDIT.md](docs/ACSL_SOURCE_LICENSE_AUDIT.md),
[docs/STATUS.md](docs/STATUS.md), and
[docs/CASP_LICENSE_REQUEST_DRAFT.md](docs/CASP_LICENSE_REQUEST_DRAFT.md).

Start with [docs/LEARNING_GUIDE.md](docs/LEARNING_GUIDE.md). Current research and
execution status live in
[docs/RESEARCH_REFRESH_2026-09-09.md](docs/RESEARCH_REFRESH_2026-09-09.md),
[docs/ENVIRONMENT_HUB_RESEARCH.md](docs/ENVIRONMENT_HUB_RESEARCH.md),
[docs/ENVIRONMENT_VALIDATION.md](docs/ENVIRONMENT_VALIDATION.md),
[docs/EXPERIMENT_PROTOCOL.md](docs/EXPERIMENT_PROTOCOL.md), and
[docs/PLAN.md](docs/PLAN.md). The compact machine-readable closure record is
[core-v1-public-release-evidence.json](environments/acsl-c/artifacts/core-v1-public-release-evidence.json).

## Repo layout

```
docs/               research findings, decision log, plan
environments/acsl-c Phase-1 environment package (verifiers v1 taskset)
  src/acsl_c/       taskset, rewards, integrity, cache, parser, spectests
  docker/           pinned Frama-C toolchain image
  examples/         sample tasks (CASP-style jsonl)
  configs/          prime-rl / eval TOML
```

## Trust statement

"Verified" here means: proof obligations discharged by pinned SMT-backed tools under
Frama-C's assumed C semantics, with specs anchored by dataset ground truth or human
approval. The VC generator and solvers are trusted (Level 1), not themselves verified.
This is documented, not hidden — see DECISIONS.md ADR-005.

## Quick start (once toolchain image exists)

```bash
docker pull ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc
uv pip install -e "environments/acsl-c[test]"
python -m pytest environments/acsl-c/tests
```

Production scoring requires a Docker or Prime sandbox. The subprocess runtime is
reserved for trusted local diagnostics.
