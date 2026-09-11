# Research Refresh: Verified RL Harness Design

## Executive conclusion

The repository's core thesis remains credible, but the next research claim must
be narrower and more disciplined than the original smoke result. The best near-
term target is fixed-contract C body completion with immutable ACSL annotations,
containerized Frama-C scoring, dense VC progress, and a fresh held-out test set.
Full contract synthesis should remain off until semantic strength is tested with
executed negative behaviors.

The implementation was updated around that conclusion: exact upstream commits,
a pinned judge image definition, cross-process caching, immutable-context checks,
corrected vacuity semantics, deterministic leakage-audited splits, current
Prime-RL configs, and a real multi-turn Bash-harness path.

## 1. Upstream harness findings

Prime-RL v0.9.0 uses typed v1 tasksets and environment sources of the form
`[[orchestrator.train.source]]`. Harness and runtime belong under each source's
`env.agent`, while task-specific configuration belongs under `env.taskset`.[^1]
Evaluation sources can reuse the same taskset with a distinct split and name.

The Verifiers task abstraction separates immutable wire data from behavior:
`TaskData` carries prompt/resources/timeouts, while decorated task methods
produce rewards and metrics.[^2] Runtime-dependent scoring receives the live
runtime explicitly. The Bash harness supplies a multi-turn shell/edit agent,
which fits formal repair better than inventing a custom conversation loop.[^3]

Local subprocess execution is useful for trusted debugging but does not isolate
side effects. Docker or a remote sandbox is therefore the production choice.[^2]
The ACSL task declares `NEEDS_CONTAINER = True`, causing configuration
compilation to reject a subprocess runtime.

Because Prime-RL and Verifiers evolve quickly, the compatibility target is:

- Prime-RL release v0.9.0, commit
  `ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1`;
- its vendored Verifiers commit
  `b2e4e8157783b2c0dffc7821044c87f29f1c3ccf`.

The vendored Verifiers commit was installed in a clean Python 3.12 environment
and exercised against the repository taskset; the Prime-RL source checkout and
its full GPU dependency graph still require the production bootstrap gate.
Tracking a moving `main` branch would make both the API and the scientific
instrument drift.[^4]

## 2. Reward design findings

Recent RL-with-verifiable-rewards work reinforces two lessons. First, reward
design details materially change optimization. DAPO highlights dynamic sampling,
token-level loss details, and overlong-sample handling in long reasoning RL.[^5]
Analysis of R1-Zero-like training identifies biases introduced by common GRPO
normalizations, including response-length effects.[^6] We should therefore log
output length, group reward variance, task difficulty, truncation, and timeout
rates rather than watching only mean reward.

Second, a verifier can be gamed. Research on RLVR reports models exploiting
verifier weaknesses, while formal-programming work reports large apparent gains
followed by specification hacking.[^7][^8] The defense cannot be “the solver said
sat/unsat.” It must bind the candidate to the intended problem and separately
measure spec strength.

The revised fixed-contract reward uses four observable components:

| Component | Weight | Purpose |
|---|---:|---|
| parse/proof gate | 0.10 | valid report, no crash, at least one VC |
| VC fraction | 0.50 | dense progress |
| complete WP+RTE proof | 0.20 | exact completion pressure |
| fixed-spec integrity | 0.20 | preserve the problem statement |

Any integrity failure zeros the whole reward. This is stronger than merely
checking that ACSL text still exists: it compares all annotations and all code
outside the selected target body.

## 3. Formal-verification findings

Frama-C 33.0 (Arsenic) is the current pinned release in this repository.[^9] Its
WP plug-in generates proof obligations from ACSL and can emit a machine-readable
JSON report used by our parser.[^10] `-wp-rte` is essential because functional
postconditions alone do not establish freedom from C run-time errors.

However, Frama-C itself stresses that a correct proof of the wrong specification
says little about the intended program.[^11] This is the central epistemic limit:

```text
solver success
  establishes the generated VCs
  under the encoded C semantics and assumptions;
it does not establish
  that the contract captures the human requirement.
```

The existing ingestion data makes this concrete. Of 399 candidates that
re-verified locally, 61 also verified after trivial-body substitution. They were
quarantined. The new split builder additionally excludes vacuity-unknown records,
two malformed body extractions, and normalized skeleton duplicates.

## 4. Specification-strength research

SpecRL's main relevant idea is negative specification testing: generate
candidate input/output behaviors that should be impossible and reward contracts
that reject them.[^12] This gives finer feedback than asking only whether one
reference implementation verifies.

Other recent systems explore LLM-generated formal specifications and iterative
repair. Re:Form studies formal specification generation and verification,[^13]
while CASP provides the source corpus used here.[^14] A recent thesis on
multi-turn formal reasoning reports that naive RLVR can rapidly improve the
verifier reward while learning specification hacks, and that filtering plus
repair feedback produces smaller but more credible gains.[^8]

Recommendation:

1. keep hints mode as the claim-bearing environment;
2. define semantic mutants or impossible behaviors offline;
3. validate those tests independently against trusted positive and negative
   implementations;
4. run them, do not award credit for merely storing them;
5. enable full-mode training only after the negative-test suite has measured
   precision/recall and survived manual audit.

E-ACSL can instrument executable subsets of ACSL for runtime checking and may be
useful as one spectest executor, but it is complementary to deductive proof and
does not cover every logic construct.[^15]

## 5. Data and evaluation findings

The original 48-example eval set has already shaped baselines and design, so it
is validation data. A new deterministic manifest creates:

- 221 train tasks;
- 47 validation tasks;
- 48 fresh test tasks;
- 21 exclusions;
- 2 duplicate groups.

The test set is stratified by VC-count difficulty and coarse program features.
This is better than row slicing, but 48 tasks still yields wide uncertainty and
the corpus remains CASP-derived. A future stronger claim should add a privately
generated or independently sourced holdout with family-level deduplication,
because exact-text deduplication does not detect semantic near-duplicates.

The old 12-step GRPO smoke is valuable engineering evidence: approximately 190
episodes reached the real Frama-C judge with zero scoring errors. The reported
0.375→0.875 reward rise is not causal learning evidence because task ordering
changed the mixture of difficulty across steps, there was no frozen paired eval,
and no checkpoint was retained.

## 6. Recommended staged program

### Stage A: instrument validation

- Build the exact Docker image and record its digest.
- Re-verify all 316 eligible references inside that image.
- Run the current unit, taskset, adversarial, and runtime smokes in CI.
- Dry-run the Prime-RL config and archive the resolved JSON.

### Stage B: establish baselines

- Keep the historical Qwen2.5-Coder-1.5B trace for comparability, then make
  Qwen2.5-Coder-7B the primary claim-bearing baseline. The managed-T4 probe
  showed 7B has substantial one-step QLoRA headroom; 14B is a separate,
  tightly budgeted ablation.
- Use task-stable sampling seeds and save raw outputs.
- Compare single-turn and eight-turn Bash-harness evaluation at matched token
  budgets.

### Stage C: controlled GRPO

- Run a 1–2 step canary, then three independent 500-step seeds.
- Track full proof, VC fraction, integrity, group variance, length, timeout,
  crash, solver time, and feature/difficulty strata.
- Select checkpoints using validation only.

### Stage D: one final test

- Freeze the repository/config/checkpoint rule.
- Evaluate the fresh test split once under the declared seeds.
- Use paired task-level comparisons and confidence intervals.
- Publish failures and reward-hacking audit, not only aggregate reward.

### Stage E: semantic strength

- Implement and validate executed negative spectests.
- Add full-mode specification synthesis only after the defense is operational.
- Explore certificate replay/audit on a sample to reduce trust in external SMT
  solvers, without putting that expensive path in the online reward loop.

## 7. What is complete and what is not

Complete locally:

- exact Verifiers dependency installs;
- 21 unit/integration-level tests pass;
- taskset loads 221/47/48/316 records for train/validation/test/all;
- a real reference scores 1.0 through Frama-C;
- an annotation mutation scores 0.0 in all components;
- SQLite verdict caching, stable IDs, split manifest, current config shape, and
  Bash-harness setup are implemented.
- Offline spectest executor and strict evidence schema are implemented; no
  spectest is enabled until independently audited negative cases run cleanly in
  the pinned image.

Not complete:

- Docker image build, digest, and live restricted-runtime smoke (completed on
  2026-09-10 after starting the existing WSL daemon);
- full-corpus re-verification inside that image;
- Prime-RL dry-run/training on the supported GPU topology;
- fresh base-model validation traces;
- executed negative spectests from audited full-mode cases;
- multi-seed claim-bearing RL and final test evaluation.

## Sources

[^1]: Prime Intellect, [Prime-RL v0.9.0 configuration](https://github.com/PrimeIntellect-ai/prime-rl/blob/ab5de8fff44b2c4a5c85e24b6e6e3f7d57eee7b1/docs/configuration.md).
[^2]: Prime Intellect, [Verifiers v1 overview](https://github.com/PrimeIntellect-ai/verifiers/blob/b2e4e8157783b2c0dffc7821044c87f29f1c3ccf/docs/overview.md).
[^3]: Prime Intellect, [Verifiers tasksets](https://github.com/PrimeIntellect-ai/verifiers/blob/b2e4e8157783b2c0dffc7821044c87f29f1c3ccf/docs/v1/tasksets.md).
[^4]: Prime Intellect, [Prime-RL releases](https://github.com/PrimeIntellect-ai/prime-rl/releases).
[^5]: Yu et al., [DAPO: An Open-Source LLM Reinforcement Learning System at Scale](https://arxiv.org/abs/2503.14476).
[^6]: Liu et al., [Understanding R1-Zero-Like Training: A Critical Perspective](https://arxiv.org/abs/2503.20783).
[^7]: [Verifier Gaming in Reinforcement Learning from Verifiable Rewards](https://arxiv.org/abs/2604.15149).
[^8]: Max Tan, [Reinforcement Learning for Formal Program Reasoning](https://arxiv.org/abs/2605.30914).
[^9]: Frama-C, [News and releases](https://www.frama-c.com/html/news.html).
[^10]: Frama-C, [WP Plug-in Manual](https://frama-c.com/download/wp-manual-27.1-Cobalt.pdf).
[^11]: Frama-C, [Dedicated specification languages](https://www.frama-c.com/2025/06/13/dedicated-specification-languages.html).
[^12]: [SpecRL: Reinforcement Learning with Formal Specification Feedback](https://arxiv.org/abs/2604.05820).
[^13]: [Re:Form—Generating Formal Specifications for Programs](https://arxiv.org/abs/2507.16331).
[^14]: [CASP: A Dataset for Code Analysis and Specification](https://arxiv.org/abs/2508.18798).
[^15]: Frama-C, [E-ACSL](https://www.frama-c.com/fc-plugins/e-acsl.html).
