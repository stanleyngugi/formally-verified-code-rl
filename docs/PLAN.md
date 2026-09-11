# Plan

## Milestone 0 — Skeleton and local judge (complete)
- [x] Repo, docs, decision log
- [x] acsl-c taskset package skeleton (loads CASP-format jsonl)
- [x] Staged reward functions (gate / VCs / full-proof / spectest slot)
- [x] Frama-C JSON report parser + stdout fallback
- [x] Dockerfile with pinned toolchain
- [x] Parser unit tests 6/6 PASS (Windows-safe, no verifiers dep needed)
- [x] Toolchain built in WSL: frama-c 33.0, why3 1.8.2, alt-ergo 2.6.3 (opam),
      z3 4.8.12 (apt); pin recorded in ADR-006
- [x] Smoke test PASSED: roundtrip on examples/sample_tasks.jsonl — task 0
      fully verified (7/7 goals incl. RTE), tasks 1-2 behave as designed.
      Known-hard: \sum/lambda goals time out at 20s (dense-reward territory)

## Milestone 1 — Hardened evaluation loop (complete locally)
- [x] Ingest CASP + vacuity filter: 338 tasks final (290/48 split); 65
      verification flips + **61 vacuous specs (15.3% of corpus!)** quarantined
      with full logs (ADR-008)
- [x] Live scoring through real frama-c via verifiers SubprocessRuntime:
      correct completion 1.000, broken control 0.100 (no LLM needed to prove
      the reward path)
- [x] Cross-process SQLite/WAL cache keyed by source + full judge policy
- [x] Fixed-annotation anti-tamper gate; all rewards zero on immutable-context edits
- [x] Deterministic leakage-audited manifest: 221 train / 47 validation / 48 test;
      one additional reference quarantined after pinned-image replay timed out
      reproducibly under the declared 20-second policy
- [x] Exact Prime-RL v0.9.0 / vendored Verifiers compatibility pin recorded;
      Verifiers install/import test passes locally (Prime-RL source install is
      still a Docker-capable-host gate; see `docs/PRIME_RL_BOOTSTRAP.md`)
- [x] Executed spectest evidence guard + offline Frama-C executor; full-mode
      spectest generation/audit remains disabled until negative cases exist
- [x] Difficulty labels: vc_estimate from CASP goals column (4–120, median 14)
- [x] Baselines (Cerebras free tier, docs/BASELINES.md): hard-slice full-proof
      gpt-oss-120b 87.5%, gemma-4-31b 62.5%; staged reward discriminates
      near-misses exactly as designed; truncation artifact caught by gate

## Milestone 2 — Multi-turn agentic mode and release validation (complete)
- [x] Bash-harness file editing with `solution.c` and `verify.sh`
- [x] Final source independently rescored; agent claims/scripts are not trusted
- [x] Turn/token/time budgets in a current standalone eval config
- [x] Optional deterministic easy-to-hard curriculum
- [x] Build the Docker image and replay all 316 eligible references serially:
      5,205/5,205 WP+RTE goals proved, zero timeouts
- [x] Validate the agentic config through Prime-RL v0.9.0 dry-run; canonical
      asynchronous GPU-host execution is optional and remains pending only if
      we decide to test Prime-RL scaling/topology
- [x] Execute the adversarial reward-hacking matrix (tampering, fake verifier,
      filesystem escape, timeout, cache poisoning, and concurrency)
- [x] Execute credit-assignment fixtures with per-turn source/verdict
      transitions and shaping ablations
- [x] Execute and retain clean negative spectest fixtures before enabling any
      specification-strength claim
- [x] Run the Verifiers v1 model-free `validate` equivalent through three fresh
      restricted-network Docker runtimes: 3/3 gold references valid
- [x] Build an isolated wheel, confirm that it bundles the corpus/manifest, and
      load a task without relying on the repository data path
- [ ] (Optional research evidence) Measure single-turn versus multi-turn under
      matched token budgets
- [x] Inspect emitted
      traces/configuration before hub packaging

## Milestone 3 — Controlled RL run
- [~] Base-model validation capture: complete 47-task deterministic
      Qwen2.5-Coder-7B generation is captured in Colab (plus an 8-task smoke
      artifact), a bounded 8-task × 4-sample stochastic rollout-shape probe is
      complete, and a four-way long-context batch memory probe passed; verified
      traces still require the production Docker/Prime topology
- [x] (Optional integration evidence) One-GPU serial LoRA/GRPO-compatible
      canary on Colab T4; report it as a `single_gpu_serial` ablation. The
      bounded run completed on one T4 with Qwen2.5-Coder-7B 4-bit + LoRA;
      loss moved `0.6463377476 -> 0.3429369628` and peak reserved memory was
      6.246 GiB. This is model/trainer evidence, not a verified reward claim.
- [x] (Optional integration evidence) 1–2 step canary with checkpoint/resume
      verification. The adapter reloaded and generated successfully at 9.047
      GiB peak; a two-rollout/one-update serial plumbing loop also passed with
      rewards explicitly marked `stub_not_verifier`.
- [ ] (Optional research evidence) Three 500-step GRPO seeds; target: paired
      held-out lift versus base model
- [x] Reward-hacking categories and credit-assignment requirements are defined
      in [`docs/ENVIRONMENT_VALIDATION.md`](ENVIRONMENT_VALIDATION.md); the
      executable fail-closed, cache/concurrency, negative-case, and trace
      rollback fixtures pass in the 42-test release suite
- [ ] Freeze checkpoint selection on validation; evaluate fresh test once
- [ ] Publish env to Environments Hub (private → public) after the public-core
      data gate below; this is not conditional on the optional GRPO study

## Milestone 3A — Public v0.1 data and publication gate

- [x] Generalize bundled data-pack selection and stable IDs; require an
      explicit local path for the non-bundled CASP research adapter
- [x] Define the public provenance schema and a wheel-payload audit that rejects
      CASP-derived code or incomplete licensing metadata
- [x] Author and replay a 16-task vertical slice across several semantic
      families, with negative cases and review status
- [x] Expand to `core-v1` (Core-64), keeping all related/template
      lineages within one split
- [x] Cold-serial replay every public reference and execute public negative
      cases in the pinned image
- [x] Build and inspect the public wheel; emit a new public-release evidence
      manifest distinct from the 316-task CASP research record
- [x] Add final code/data licenses, `CITATION.cff`, notices, maintainer,
      security policy, and public URLs
- [ ] Publish the judge image by digest, push the environment privately to
      Prime, validate a clean Hub install, then make the GitHub release, Hub
      listing, dataset card, and blog public
- [ ] Continue the CASP permission/provenance request in parallel; if cleared,
      publish CASP only as a separately versioned expansion pack
- [ ] Ingest the pinned MIT-licensed ACSL by Example source into a separately
      attributed candidate pack; establish the usable task count through our
      own Frama-C 33 replay rather than CASP's historical file counts
- [ ] Build a per-file license-ledger join before using any SV-COMP-derived ACSL
      material; keep GPL and permissive packs separate
- [ ] Treat X509-parser as a future BSD-attributed multi-file/long-horizon pack,
      not as an isolated-function shortcut
- [ ] Request license clarification for WP tutorial, Frama-C Problems, ACSL
      Proved, and VecoSet before copying any of their material

## Milestone 4 — Phase 2: Verus environment (weeks 10+)
- [ ] Port rubric to Verus (`--format json`, per-function entries; crash-tolerant
      per issue #2645)
- [ ] Seed data: Dafny2Verus translations + SAFE/VeRuSyn-style synthesis pipeline

## Standing risks
| Risk | Mitigation |
|---|---|
| Spec hacking inflates rewards | r4 spectests; implication checks; audits each run |
| Solver nondeterminism/timeouts | pinned image, per-goal timeout, cache by digest |
| verifiers v1 API churn | exact commit paired with Prime-RL release; install/API smoke per bump |
| Throughput (solver wall-clock) | caching, -wp-fct selection, short-task curriculum first |
| Data contamination | stable manifest now; add private family-level holdout before broad claims |

## Current execution boundary

Managed Colab proved model loading, QLoRA optimizer feasibility, and
deterministic prompt/output capture on a T4. Claim-bearing verification is now
also operational locally: native Frama-C, the pinned Docker image, the exact
Prime-RL/Verifiers checkout, Prime's dry-run, and Verifiers v1's model-free
container validation all pass. The release preflight therefore reports
`environment_release_ready=true`.

An asynchronous two-process Prime-RL run is needed only if we want to test
Prime-RL's asynchronous orchestration, throughput, or scaling behavior. That
run should happen on a Docker-capable Linux GPU host (or a Colab local runtime
backed by one), but it is not an environment-correctness prerequisite. The
preserved image digest is already the verification gate; a hardened image
rebuild is optional and not a prerequisite for using Colab's GPU. The exact
source install is documented in `docs/PRIME_RL_BOOTSTRAP.md`; a training
improvement claim still requires the frozen held-out protocol.

The environment release itself is governed by
[`docs/ENVIRONMENT_VALIDATION.md`](ENVIRONMENT_VALIDATION.md). It requires
independent verifier, isolation, data, reward, adversarial, and reproducibility
evidence; it does not require a long multi-seed training campaign. Training
milestones below are optional research evidence unless the project explicitly
claims a learning improvement.

## Definitions of done

The **technical environment-infrastructure claim on the research corpus is
complete** as of 2026-09-10. The machine-readable record is
[`release_evidence_2026-09-10.json`](../environments/acsl-c/artifacts/release_evidence_2026-09-10.json).
That record is not the public-corpus release manifest. Public distribution of
the current wheel is not cleared because the CASP-derived records do not retain
per-file source/license metadata, and CASP's own card directs users to check The
Stack source licenses. The selected independent release path is an explicitly
licensed, project-authored `core-v1`; CASP remains a non-bundled adapter while
permission/provenance work continues. The detailed architecture and novelty
boundary are in `docs/PUBLICATION_STRATEGY.md` and `docs/RELATED_WORK.md`.

A separate, optional **learning-improvement claim** would require: “A model
trained in our environment shows a statistically significant increase in
Frama-C-verified solutions on a fresh held-out split, with no increase in
vacuous-spec rate.” Multi-seed GRPO, matched prompt ablations, and one-time test
evaluation belong to that future paper-level claim, not to environment release.
