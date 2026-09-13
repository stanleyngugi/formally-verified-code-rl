# Formally Verified C v0.1.7

Formally Verified C is the first environment in the Formally Verified Code RL
project. It is a Verifiers v1 taskset for completing C functions under fixed
ACSL contracts and scoring candidates with Frama-C WP plus runtime-error proof
obligations.

This is the recommended alpha release. It hardens the trust boundary between
the in-container verifier runner and the reward process. Core-v1 remains at
dataset version 0.1.4 because its 64 task records, references, negatives, and
family-isolated splits are unchanged.

## What changed

- A serialized `ok: true` is now reconciled against every required invariant:
  successful parsing and compilation, valid nonnegative counts, at least one
  goal, no crash, a clean process exit, no timeout, no reported failure, and
  every goal proved.
- Missing or non-Boolean success fields, malformed goal records, non-integer
  timeout fields, negative timeouts, impossible goal/RTE counts, and
  inconsistent declared failure counts fail closed.
- The parse/compile gate and fractional-progress reward now require a coherent,
  compiled, clean-exit report. A cleanly reported solver timeout may expose
  partial VC progress, but can never earn full-proof or specification-strength
  reward.
- Contradictory reports and nonzero process exits are neither rewarded nor
  cached. The runner source digest in the cache key changes automatically with
  this policy update.
- The blog now states explicitly that fixed-contract integrity/strength credit
  is proof-gated rather than an independent reward for merely preserving text.

## Release artifacts

- Source: <https://github.com/stanleyngugi/formally-verified-code-rl>
- Prime environment:
  <https://app.primeintellect.ai/dashboard/environments/stanley-ngugi/formally-verified-c>
- Dataset: <https://huggingface.co/datasets/stan4u/formally-verified-c-core-v1>
- Judge tag: `ghcr.io/stanleyngugi/formally-verified-c-judge:0.1.4`
- Immutable judge image:
  `ghcr.io/stanleyngugi/formally-verified-c-judge@sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593`
- Canonical GitHub release wheel:
  `formally_verified_c-0.1.7-py3-none-any.whl`
- Canonical wheel SHA-256:
  `5afae1e9078de85f0ecb4b0c26d918c0e39c33f7cecc7f0dfadcc7596eadc68d`
- Prime-built wheel SHA-256:
  `9917cf2d7c570bdc49983d04395c1fe6c7249691e9f518b01eb2edf54c3416a0`
- Prime content hash: `4fe4927e56c6`

Prime builds the wheel again during upload. The two v0.1.7 wheel archives have
the same 16 member paths and identical content for every member; their outer
ZIP hashes differ because the builds carry different archive metadata. Both
are 39,174 bytes.

## Executed evidence

- 64 project-authored Apache-2.0 tasks; split 33 train / 15 validation / 16 test.
- 64/64 references prove: 296/296 total goals and 84/84 runtime-safety goals.
- 64/64 deliberately wrong controls parse and compile, then fail proof.
- Zero solver timeouts across both corpus replay gates.
- 57/57 tests pass under Linux, the supported Verifiers v1 platform.
- Ruff and Python compilation checks pass.
- An isolated install of the canonical wheel loads all 64 bundled Core-v1
  tasks without a repository-relative data path.
- The exact Prime v0.1.7 source archive passed source, secret, provenance, and
  prohibited-payload audits before import; its own 57-test suite then passed
  and its public loader constructed all 64 tasks.
- The public wheel and Prime source archive contain Core-v1 and no CASP-derived
  task payload.

## Claim boundary

“Formally verified” means the released references discharge the declared
Frama-C WP and runtime-error obligations under the stated policy. The verifier
stack and parser remain in the trusted computing base. Core-v1 is
machine-reviewed and machine-verified, not independently expert-reviewed; this
release makes no model-improvement or state-of-the-art-training claim.
