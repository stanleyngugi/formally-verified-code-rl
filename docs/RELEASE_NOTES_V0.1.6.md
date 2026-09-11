# Formally Verified C v0.1.6

Formally Verified C is the first environment in the Formally Verified Code RL
project. It is a Verifiers v1 taskset for completing C functions under fixed
ACSL contracts and scoring candidates with Frama-C WP plus runtime-error proof
obligations.

This is the recommended alpha release. It supersedes v0.1.5 by making the
Prime source-archive bytecode exclusions explicit and recording a pristine
pull audit before any module import can generate local bytecode. It otherwise
retains the v0.1.5 judge correction: every runtime configuration
uses the immutable image rebuilt from the checked-in Dockerfile. Core-v1 stays
at dataset version 0.1.4 because its 64 task records and manifest are unchanged.

## Release artifacts

- Source: <https://github.com/stanleyngugi/formally-verified-code-rl>
- Prime environment:
  <https://app.primeintellect.ai/dashboard/environments/stanley-ngugi/formally-verified-c>
- Dataset: <https://huggingface.co/datasets/stan4u/formally-verified-c-core-v1>
- Judge tag: `ghcr.io/stanleyngugi/formally-verified-c-judge:0.1.4`
- Immutable judge image:
  `ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593`
- Wheel: `formally_verified_c-0.1.6-py3-none-any.whl`
- Wheel SHA-256:
  `833cb13adc826ddfe7a3c7604d0e6425b51750cd5110aad2ae3843d6a4ebcb1c`

## Executed evidence

- 64 project-authored Apache-2.0 tasks; split 33 train / 15 validation / 16 test.
- 64/64 references prove: 296/296 total goals and 84/84 runtime-safety goals.
- 64/64 deliberately wrong controls parse and compile, then fail proof.
- Zero solver timeouts across both replay gates.
- 42/42 tests pass under Linux, the supported Verifiers v1 platform.
- The public wheel and exact Prime source archive contain Core-v1 and no
  CASP-derived task payload.

The top-level proof stack is Frama-C 33.0 (Arsenic), Why3 1.8.2,
Alt-Ergo 2.6.3, and Z3 4.8.12. The OCI digest is the complete binary/runtime
identity; compatible OPAM transitive build dependencies are not claimed to be
independently source-locked.

## Claim boundary

“Formally verified” means the released references discharge the declared
Frama-C WP and runtime-error obligations under the stated policy. The verifier
stack and parser remain in the trusted computing base. Core-v1 is
machine-reviewed and machine-verified, not independently expert-reviewed; this
release makes no model-improvement or state-of-the-art-training claim.
