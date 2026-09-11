# Formally Verified C v0.1.4

Formally Verified C is the first environment in the Formally Verified Code RL
project. It is a Verifiers v1 taskset for completing C functions under fixed
ACSL contracts and scoring candidates with Frama-C WP plus runtime-error proof
obligations.

This is an alpha environment release. It establishes a usable, audited
environment and public task pack; it does not claim that a particular RL run
improves a model.

## Release artifacts

- Source: <https://github.com/stanleyngugi/formally-verified-code-rl>
- Prime environment:
  <https://app.primeintellect.ai/dashboard/environments/stanley-ngugi/formally-verified-c>
- Dataset: <https://huggingface.co/datasets/stan4u/formally-verified-c-core-v1>
- Judge image: `ghcr.io/stanleyngugi/formally-verified-c-judge:0.1.4`
- Immutable judge image:
  `ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:5da598c4fa7f1e4210412822f3c3942764baa0057e85070ab5d3b1fadd1ac9dc`
- Wheel: `formally_verified_c-0.1.4-py3-none-any.whl`
- Wheel SHA-256:
  `27e77462fde7d4ddcdaf7a46a3c5aa4a8ad3e05033fb9ec35fe87a04057bfc41`

## Core-v1 evidence

- 64 project-authored Apache-2.0 tasks.
- Split: 33 train / 15 validation / 16 test.
- Semantic and derivation families are isolated to one split.
- 64/64 reference implementations fully prove.
- 296/296 total proof goals and 84/84 runtime-safety goals prove.
- Zero solver timeouts in the reference replay.
- 64/64 deliberately wrong controls parse and compile, then fail proof.
- Zero solver timeouts in the deterministic negative replay.
- 42/42 tests pass in both the working tree and the exact clean source archive
  pulled back from Prime.

Pinned proof stack:

- Frama-C 33.0 (Arsenic)
- Why3 1.8.2
- Alt-Ergo 2.6.3
- Z3 4.8.12

The authoritative compact evidence is
[`environments/acsl-c/artifacts/core-v1-public-release-evidence.json`](../environments/acsl-c/artifacts/core-v1-public-release-evidence.json).

## Public-data boundary

The wheel and Prime source archive contain the project-authored Core-v1 pack
and no CASP-derived task payload. The larger 316-task CASP corpus remains a
research-only adapter because the available snapshot does not provide enough
record-level repository, revision, author, and license provenance to establish
redistribution rights.

The public GitHub branch is a new root history assembled from the audited
public tree. This prevents earlier locally tracked research data from appearing
in public Git history.

## Installation

```bash
prime env install stanley-ngugi/formally-verified-c
```

For source development:

```bash
git clone https://github.com/stanleyngugi/formally-verified-code-rl.git
cd formally-verified-code-rl/environments/acsl-c
uv sync --extra test
uv run pytest -q
```

The Verifiers v1 entry points are `load_taskset(config)` and
`load_environment(config)`. The public name is `formally-verified-c`; the
internal `acsl_c` namespace remains as a compatibility alias.

## Claim boundary

“Formally verified” means that the released reference programs discharge the
declared Frama-C WP and runtime-error proof obligations under the pinned policy.
Frama-C, Why3, the provers, their models, the container boundary, and the result
parser are part of the trusted computing base; the verifier stack is not itself
claimed to be formally verified.

Core-v1 is machine-reviewed and machine-verified, not yet independently
expert-reviewed. The release does not claim comprehensive C coverage, model
improvement, state-of-the-art training, or uniqueness across all prior work.
