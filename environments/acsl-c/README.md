# Formally Verified C

An RL environment for generating C implementations that satisfy fixed ACSL
contracts. Model output is judged by Frama-C WP+RTE under a pinned toolchain.
The public package and Prime Hub slug are `formally-verified-c`; `acsl_c`
remains the internal compatibility namespace.

## Current status

Technical and public-data validation are complete for v0.1. The wheel bundles
the project-authored Apache-2.0 Core-v1 and excludes CASP-derived task payload.
CASP remains a non-bundled research adapter until its per-file rights can be
reconstructed or permission is obtained.

- Exact API target: Prime-RL v0.9.0 plus its vendored Verifiers commit.
- Public Core-v1: 33 train / 15 validation / 16 test (64 total).
- Public proof replay: 64/64 references, 296/296 goals, 84/84 RTE goals,
  zero timeouts; 64/64 deterministic negative cases rejected.
- Research-only CASP corpus: 221 train / 47 validation / 48 test; 22 excluded.
- Reward: parse gate 0.10, VC fraction 0.50, full proof 0.20, fixed-spec
  integrity 0.20.
- Persistent SQLite/WAL verdict cache includes source, prover policy, timeout,
  runner schema, and full toolchain ID in its key.
- Single-turn `null` and multi-turn `bash` harness modes are implemented.
- Hints-mode fixed-contract completion is release-ready. Full specification
  synthesis remains deliberately disabled; its accepted/rejected executor
  contract now has a clean negative fixture, but it is a future task family.

See the repository's `docs/LEARNING_GUIDE.md` for concepts and
`docs/EXPERIMENT_PROTOCOL.md` before running a claim-bearing experiment.
For the environment-specific release gates—especially reward hacking,
credit assignment, prompt boundaries, and what does *not* require a long RL
run—see `docs/ENVIRONMENT_VALIDATION.md`.

## Layout

```text
src/acsl_c/taskset.py       typed taskset and reward hooks
src/acsl_c/integrity.py     immutable-context / annotation checks
src/acsl_c/framac.py        stable Frama-C verdict parser
src/acsl_c/verify_script.py isolated runtime runner
src/acsl_c/cache.py         cross-process verdict cache
src/acsl_c/spectests.py     conservative strength policy
scripts/ingest_casp.py      re-verification and vacuity quarantine
scripts/build_splits.py     deterministic split manifest
scripts/replay_references.py resumable production-image reference replay
configs/train.toml          supported two-GPU GRPO config
configs/agentic_eval_v0_9.toml multi-turn validation config
configs/validate.toml       model-free Verifiers v1 container release smoke
docker/Dockerfile           pinned judge image definition
```

## Data contract

Public data are JSONL records in `data/packs/core-v1`, selected by that pack's
`manifest.json`. Important fields include `mode`, `skeleton_c`,
`reference_solution`, `negative_cases`, provenance and license fields, semantic
and derivation families, `non_vacuous`, and `data_schema_version`. Explicit
research directories retain compatibility with the older CASP schema; those
records are never bundled implicitly.

Public tasks use explicit stable IDs. Imported research tasks use a dataset
namespace plus a SHA-256 digest of normalized reference source rather than a
mutable row number.

## Local validation

The primary deliverable is a correct, isolated, reproducible environment. A
long multi-seed GRPO campaign is optional research evidence, not a prerequisite
for validating this taskset. Run the adversarial and credit-assignment fixtures
described in `docs/ENVIRONMENT_VALIDATION.md` in addition to the happy-path
smokes below.

Run inside Linux/WSL with Python 3.12 and uv:

```bash
uv venv /tmp/acslc-venv --python 3.12
uv pip install --python /tmp/acslc-venv/bin/python -e '.[test]'
/tmp/acslc-venv/bin/python -m pytest -q
/tmp/acslc-venv/bin/python scripts/smoke_taskset.py
eval "$(opam env)"
/tmp/acslc-venv/bin/python scripts/live_runtime_smoke.py
uv run python scripts/preflight.py --prime-root /workspace/prime-rl
```

The `live_runtime_smoke.py` command intentionally uses a host subprocess only
with trusted reference data. Never use that runtime for model-generated
output. `preflight.py` is read-only apart from an optional report file. Its
default exit gate is environment release readiness; `--require async`
additionally requires two locally visible GPUs.

## Container and training

```bash
docker pull ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc
docker image inspect ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc --format '{{.Id}}'
docker run --rm -v "$PWD:/workspace/acsl-c" ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc \
  python3 /workspace/acsl-c/scripts/replay_references.py \
  --data-dir /workspace/acsl-c/data --split all --jobs 1 \
  --output /workspace/acsl-c/artifacts/reference-replay.jsonl \
  --summary /workspace/acsl-c/artifacts/reference-replay.summary.json

# From the pinned Prime-RL v0.9.0 checkout:
uv run --no-sync validate @ /workspace/acsl-c/configs/validate.toml
uv run --no-sync rl @ /workspace/acsl-c/configs/train.toml --dry-run True
uv run rl @ /workspace/acsl-c/configs/train.toml
```

`configs/train.toml` assumes two GPUs: one trainer and one inference GPU. The old
16 GB single-GPU TOML is retained only as a historical record of the 2026-08-25
smoke and depends on now-obsolete local Prime-RL patches.

## Safety boundaries

- `AcslCTask.NEEDS_CONTAINER = True` rejects subprocess production configs.
- The model may change only the target function body in hints mode.
- Scoring independently invokes the pinned runner; it does not trust an agent's
  edited `verify.sh` or textual claim.
- Unknown vacuity and malformed extraction are excluded from research splits.
- Release configs use an empty runtime network allow-list; the release smoke
  confirms direct egress is blocked and the host workspace is not mounted.
- The wheel bundles the canonical corpus shards, split manifest, and exclusions,
  so hub installation does not depend on a developer checkout path.
