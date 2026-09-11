# Decision Log (ADR-style)

Each decision: context, decision, consequences. Newest at bottom.

---

## ADR-001 — Reward = formal verification, not unit tests

**Context:** Code-RL judges are unit tests (samples) or LLM judges (subjective).
Auto-active verifiers give deterministic all-inputs verdicts on disciplined subsets.
**Decision:** Build RL environments whose primary reward is SMT-backed formal
verification (Frama-C/WP for C, Verus for Rust). Unit tests remain as a *secondary*
metric only (AxDafny shows verification and test performance measure different things;
we want both visible).
**Consequences:** Rewards are sound within the toolchain's assumed semantics; coverage
is limited to verifiable subsets; solver wall-clock becomes a throughput constraint.

## ADR-002 — Language order: C/ACSL first, Verus second, Dafny third

**Context:** Alternatives ranked by (a) seed data availability, (b) judge automation,
(c) commercial relevance, (d) ecosystem gap.
**Decision:** Phase 1 = C+ACSL (CASP 506 pairs ready; SV-COMP pool; no existing RL env
— biggest novelty; CompCert exists beneath the stack). Phase 2 = Rust/Verus (strongest
community + industrial pull). Phase 3 = Dafny (cheap port; transfer data for Verus).
Lean deferred: judge sparsity is a missing-library problem; revisit once platform funds
formalization work (see ADR-007).
**Consequences:** C's ACSL is more verbose than Dafny specs and Frama-C slower than
Dafny CLI; mitigated by caching and per-function selection flags.

## ADR-003 — Harness: Prime Intellect verifiers v1

**Context:** Need rollout infra, multi-turn agent harnesses, sandboxed runtimes,
TOML-configured training via prime-rl. Alternatives: roll our own, veRL directly,
Harbor.
**Decision:** Target `verifiers.v1` taskset API exclusively (v0 deprecated). Use
in-runtime execution so verifier dependencies live in the sandbox image only.
The dependency-free scoring runner executes with the image's pinned system
Python; the generic `run_uv_script` helper is intentionally avoided because its
runtime package-manager preparation conflicts with the unprivileged,
network-restricted judge.
**Consequences:** Coupled to a fast-moving v1 API; pin verifiers version in
pyproject; smoke-test against each release.

## ADR-004 — Staged reward shape

**Decision:** Four components (weights in code, tunable via config):
1. parse/compile gate (0.10)
2. fraction of proof obligations discharged (0.50) — dense signal from WP JSON /
   Verus function entries
3. full verification incl. RTE guards (0.20)
4. spec strength via spectests (0.20) — anti-Goodhart per SpecRL
Tool crash ⇒ reward 0 + crash metric; never an exception escaping the reward fn.
**Consequences:** r2 alone can be farmed by trivial annotations; r4 gates it.
Spectest generation is offline per-task; tasks without spectests score max(0, r1..r3).

## ADR-005 — Trust stance: documented Level-1, upgrade path to Level-2

**Context:** The VC generator (WP plugin), translation to Why3/SMT, and solvers are
trusted, unverified code. Solver bugs exist (Alive2 found 24 in Z3).
**Decision:** Be explicit in README/docs that "verified" means "VCs discharged under
assumed semantics with trusted tools." Do NOT market as machine-checked theorem.
Upgrade path: where fragments allow, cross-check unsat results via certificate
reconstruction (cvc5 CPC → checker; later lean-smt) as an audit mode, not the hot-path
reward.
**Consequences:** Honest claims; audit mode adds compute only when enabled.

## ADR-006 — Pin the entire judge toolchain

**Decision:** Docker image pins Frama-C, Why3, Alt-Ergo, and Z3 versions, and (for
Phase 2) verus release; image digest recorded here and embedded in cache keys.
Any bump requires re-verifying the whole corpus and a new ADR note.

**Phase-1 toolchain pin (2026-08-24, WSL Ubuntu 24.04 build):**

| Component | Version | Source |
|---|---|---|
| Frama-C | 33.0 (Arsenic) | opam |
| Why3 | 1.8.2 | opam |
| Alt-Ergo | 2.6.3 | opam |
| Z3 | 4.8.12 | apt (matches CASP's original verification) |
| cvc5 | dropped from defaults | absent; frama-c aborts on unknown provers |

Notes:
- Noble repos ship no frama-c/alt-ergo; opam is the reproducible path.
- Unknown prover names are fatal (`Unknown prover cvc5` aborts the run) — prover
  lists must be validated against the installed set before reward runs.
- WP maintains an on-disk proof cache across invocations; content-hash caching in
  the env must account for cold vs warm first runs.

**Consequences:** Reproducible rewards across training runs; occasional manual
upgrade work.

## ADR-007 — ITP integration deferred but bridged, not ignored

**Context:** Deepest verified artifacts live in Rocq/Isabelle/HOL4; Lean kernel works
as RL judge for math; code-side formalizations in Lean are missing; lean-smt/cvc5 CPC
reconstruction exists in beta.
**Decision:** No Lean-native env now. Add optional "audit" rubric component later:
reconstruct cvc5 proofs of discharged VCs into Lean (lean-smt) on sampled tasks to
measure judge agreement. Long-term option: fund a disciplined-C-subset Rocq/Lean
formalization to make the reward chain foundational.
**Consequences:** None near-term; keeps strategic door open.

## ADR-008 — Data hygiene rules

**Decision:** Every training task must have: (1) verified ground truth under OUR
pinned image (re-verify CASP on import; record flips), (2) spec-strength metadata
(has spectests? implication-checked?), (3) difficulty label (VC count, loop depth),
(4) provenance field. Tasks failing re-verification are quarantined, not silently
dropped.
**Consequences:** Slower ingestion, honest evals, contamination tracking.

## ADR-009 — Agentic harness as the target mode

**Context:** Prior work is mostly single-shot or fixed repair loops.
**Decision:** Primary target mode = multi-turn: the model gets verifier diagnostics
and named failed obligations in context and edits files in the sandbox across turns.
The harness stops when the model finishes or its declared turn/token budget is
exhausted. Single-turn scoring is kept for cheap evaluation.
**Consequences:** Matches real usage; differentiates from published single-shot work;
higher rollout cost per sample.

## ADR-010 — Freeze Prime-RL v0.9.0 with its vendored Verifiers commit

**Context:** Upstream configuration and typed APIs changed materially after the
original 0.3.0 integration. Pinning Verifiers alone can still mismatch Prime-RL.
**Decision:** Treat Prime-RL commit
`ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1` and Verifiers commit
`b2e4e8157783b2c0dffc7821044c87f29f1c3ccf` as one compatibility unit. Use the
v0.9 source-shaped `env.taskset` / `env.agent` config and reject production
subprocess execution.
**Consequences:** Reproducible APIs and configs; upgrades are explicit migration
events with install, dry-run, and real-judge tests.

## ADR-011 — Historical eval becomes validation; fresh manifest test

**Context:** The old 48-task eval split informed baseline and design decisions,
so it cannot support an unbiased final claim. Row-order slicing also confounded
the first smoke curve.
**Decision:** Preserve 47 eligible historical-eval tasks as validation. Select a
fresh 48-task test from the historical train pool, stratified by VC difficulty
and coarse features. Exclude vacuity-unknown, malformed extraction, and exact
normalized skeleton duplicates. Store stable content IDs in a manifest.
**Consequences:** Honest checkpoint selection and a one-use final test, at the
cost of a smaller 221-task training set after production replay quarantine. A future independent/private holdout is
still needed for strong generalization claims.

## ADR-012 — Fixed contracts now; full spec synthesis waits for executed spectests

**Context:** Structural annotation preservation solves spec editing only when the
task provides a trusted fixed contract. Stored or heuristic spectests that are
not executed provide no semantic assurance.
**Decision:** Hints-mode rewards require exact ACSL and immutable-context
integrity. Full mode is disabled by default and missing/unexecuted spectests earn
zero strength credit. Enable full mode only after negative behaviors are
generated, independently validated, and executed against candidate contracts.
**Consequences:** Near-term claims are narrower but defensible. Semantic
specification synthesis remains a research milestone, not a hidden stub.

## ADR-013 — Reference eligibility is defined by cold serial production replay

**Context:** A four-worker replay can create CPU contention that changes whether
an SMT query reaches its 20-second limit. One 112-goal reference alternated
between fully proved and one timeout under concurrent replay, while passing cold
and serially. A different reference (`casp:75`) timed out both concurrently and
alone at 20 seconds, but proved at 60 seconds.

**Decision:** Corpus eligibility uses a cold, one-worker replay in the pinned
image with the same 20-second per-goal policy used for reward. Concurrency is a
required evidence field. References that fail cold and serially are retained in
the source corpus but listed in `data/replay_exclusions.jsonl`; they cannot enter
train, validation, or test manifests.

**Consequences:** The eligible corpus is 221 train / 47 validation / 48 test.
The authoritative replay proves 316/316 references and 5,205/5,205 reported
goals, including 1,264/1,264 RTE goals, with zero timeouts. Parallel replay is a
throughput diagnostic only and cannot establish eligibility.

## ADR-014 — Public release uses explicit data packs, not bundled CASP

**Context:** CASP was the strongest available engineering seed and enabled a
316-task production replay, but the available Stack-derived records omit the
original repository/path/revision/license needed for defensible redistribution.
Dynamic downloading avoids bundling but does not itself establish downstream
rights. An explicitly MIT-licensed ACSL by Example collection exists, but is
smaller and pedagogical. The environment can be released independently of a
large training claim.

**Decision:** The default public v0.1 wheel will contain a project-authored,
human-reviewed `core-v1` with explicit data licensing, lineage-aware splits,
and negative cases. CASP becomes a non-bundled adapter requiring an explicit
user-supplied path until written permission or a complete compatible-license
provenance map is available. Clearly licensed external collections may be
added only as separately attributed packs. GitHub is the canonical source;
Prime's Environments Hub is the registry/discovery surface; the judge ships as
an immutable OCI image.

**Consequences:** A new public-core replay and wheel evidence record are still
required, so the current CASP-bundled wheel remains non-public. The project no
longer waits indefinitely on CASP clearance, the public data chain is auditable,
and later CASP or expert long-horizon packs can expand the environment without
changing its verifier API.
