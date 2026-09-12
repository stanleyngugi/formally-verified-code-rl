# Project status — 2026-09-12

## Bottom line

The ACSL-C environment and its redistributable public corpus are technically
ready for an initial release. Core-v1 contains 64 project-authored Apache-2.0
tasks and the wheel contains no CASP-derived task payload. A long or
asynchronous RL campaign is not an environment-release requirement.

The release is deliberately described as machine-reviewed and
machine-verified. Independent human review is still invited and must not be
implied by the v0.1 evidence. The optional training paper, broader corpora, and
two-GPU throughput work remain follow-on research rather than blockers.

## Completed

- Public Core-v1: 64 tasks, split into 33 train / 15 validation / 16 test with
  semantic and derivation families confined to one split.
- Every public record carries stable identity, origin URL, intended release
  revision, source path, normalized content hash, Apache-2.0 license,
  transformation, family, and review metadata.
- Public cold replay: 64/64 references fully proved, 296/296 total proof goals,
  84/84 RTE goals, and zero solver timeouts under Frama-C 33.0, Why3 1.8.2,
  Alt-Ergo 2.6.3, and Z3 4.8.12.
- Public negative gate: 64/64 plausible wrong implementations parse and
  compile, then fail the deterministic WP+RTE/Qed proof pass with zero
  timeouts.
- The package exports the current Verifiers v1 `load_taskset(config)` and
  `load_environment(config)` entry points while retaining plugin-class loading.
- An isolated site-packages install loads all 64 tasks and constructs the
  standard `SingleAgentEnv` without a repository data path.
- The public wheel bundles Core-v1 and its dataset card, manifest, and task
  records; its payload audit finds no CASP data.
- Full local suite: 42 passed; Ruff and Python compilation checks pass.
- Apache-2.0 license, notice, citation, security policy, contribution guide,
  maintainer identity, repository URL, dataset card, blog draft, and
  machine-readable public-release evidence are present.
- Research-only validation remains preserved separately: 316 admitted CASP
  tasks replayed at 5,205/5,205 proof goals and 1,264/1,264 RTE goals with zero
  timeouts. Those records are not part of the public wheel.
- Colab T4 evidence established Qwen2.5-Coder-7B 4-bit LoRA optimizer,
  checkpoint, and serial plumbing feasibility. It is not a learning-lift or
  verifier-scored training claim.

## Publication status

- The canonical GitHub repository is public at
  `https://github.com/stanleyngugi/formally-verified-code-rl`; v0.1.4 is the
  historical first prerelease and v0.1.6 is the recommended alpha release.
- The exact Core-v1 mirror and dataset card are public at
  `https://huggingface.co/datasets/stan4u/formally-verified-c-core-v1`.
- The rebuilt judge is public at immutable digest
  `sha256:b7d7111eac04eb09405842b64af5084f671c8815f90a3d9ea7f5de92f0bcd593`.
  A credential-free Docker pull by digest succeeds.
- Prime environment v0.1.6 is public. Its pristine source archive contains no
  bytecode or research payload; the source audit passes, 42/42 tests pass, and
  the public loader constructs a one-task `AcslCTaskset`. Prime's unauthenticated
  status endpoint reports `PUBLIC` and content hash
  `a8e90d5be870b7fb8e70f8387786d83754adee83b0b1d9d8335c9b34ea89b8cb`.
- The publication-ready blog draft contains the final names, verified URLs,
  evidence, scope, limitations, related-work positioning, GPU-experiment
  interpretation, and roadmap. All linked release surfaces are public; posting
  the article on the selected blog platform is the only remaining launch work.

## Deliberately deferred

- Independent human/expert review of all 64 tasks. Until recorded, use
  “machine-reviewed and machine-verified,” not “expert-reviewed.”
- CASP redistribution. The available snapshot lacks the original per-file
  repository/license fields needed for a public derived corpus.
- ACSL by Example ingestion, per-file SV-COMP licensing joins, and X509
  multi-file tasks. These are separately attributed future packs, not material
  silently mixed into Core-v1.
- Multi-seed GRPO, frozen checkpoint selection, one-time held-out evaluation,
  and a learning-improvement claim.
- Async/two-GPU scaling. It measures throughput topology, not correctness of
  the environment or reward.

The authoritative public record is
`environments/acsl-c/artifacts/core-v1-public-release-evidence.json`. The older
`release_evidence_2026-09-10.json` remains the CASP-based research-engineering
record and must not be cited as the public task count.
