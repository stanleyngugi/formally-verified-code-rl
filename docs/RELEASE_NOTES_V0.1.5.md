# Formally Verified C v0.1.5

Formally Verified C is the first environment in the Formally Verified Code RL
project. It is a Verifiers v1 taskset for completing C functions under fixed
ACSL contracts and scoring candidates with Frama-C WP plus runtime-error proof
obligations.

This patch release supersedes v0.1.4 as the recommended environment package.
It rebuilds the judge from the checked-in Dockerfile, publishes the resulting
immutable digest in every runtime configuration, and repeats the reference and
negative-control replays against that exact image. Core-v1 itself remains
dataset version 0.1.4 because its task records and manifest are unchanged.

## Release artifacts

- Source: <https://github.com/stanleyngugi/formally-verified-code-rl>
- Prime environment:
  <https://app.primeintellect.ai/dashboard/environments/stanley-ngugi/formally-verified-c>
- Dataset: <https://huggingface.co/datasets/stan4u/formally-verified-c-core-v1>
- Judge image: `ghcr.io/stanleyngugi/formally-verified-c-judge:0.1.4`
- Immutable judge image:
  `ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593`
- Wheel: `formally_verified_c-0.1.5-py3-none-any.whl`
- Wheel SHA-256:
  `1b56ea3403f2325962e89a0790ac0a863645eb7380cc2a2968e1ba89c73bdc60`

## Core-v1 evidence

- 64 project-authored Apache-2.0 tasks.
- Split: 33 train / 15 validation / 16 test.
- Semantic and derivation families are isolated to one split.
- 64/64 reference implementations fully prove.
- 296/296 total proof goals and 84/84 runtime-safety goals prove.
- 64/64 deliberately wrong controls parse and compile, then fail proof.
- Zero solver timeouts across both replay gates.
- 42/42 tests pass under Linux, the supported Verifiers v1 platform.

The top-level proof stack is Frama-C 33.0 (Arsenic), Why3 1.8.2,
Alt-Ergo 2.6.3, and Z3 4.8.12. The immutable image digest is the complete
binary/runtime identity; compatible OPAM transitive build dependencies are not
claimed to be independently source-locked.

## Public-data and claim boundary

The wheel and Prime source archive contain project-authored Core-v1 and no
CASP-derived task payload. The larger CASP corpus remains research-only until
record-level redistribution provenance is available.

“Formally verified” means the released reference programs discharge the
declared Frama-C WP and runtime-error obligations under the stated policy. The
verifier stack and result parser remain in the trusted computing base. Core-v1
is machine-reviewed and machine-verified, not independently expert-reviewed;
this release makes no model-improvement or state-of-the-art-training claim.
