# Related work and novelty boundary

> Living draft, refreshed 2026-09-11. This is a publication aid, not an
> exhaustive systematic review. Refresh the searches and verify every version
> immediately before publication.

## Why this comparison needs narrow categories

“Formal verification plus AI” covers several different artifacts:

- a benchmark can supply specifications and reference programs;
- an inference scaffold can query a verifier repeatedly at test time;
- a training study can optimize a model with verifier-derived reward;
- an RL environment package can expose tasks, lifecycle, isolation, reward,
  metrics, and installation as reusable infrastructure;
- a theorem-proving environment can generate proofs without synthesizing an
  imperative C implementation;
- a specification-synthesis system can generate contracts for existing code,
  which has a different anti-cheating problem from completing code under a
  fixed contract.

Treating all of these as interchangeable either erases the novelty of ACSL-C or
creates an exaggerated priority claim. The defensible comparison is at the
artifact and task level.

## Comparison matrix

| Work | Language / verifier | Primary artifact and task | Iterative verifier feedback | RL optimization | Public reusable RL environment is the stated contribution? | Relationship to ACSL-C |
|---|---|---|---:|---:|---:|---|
| [VeCoGen](https://arxiv.org/abs/2411.19275) | C + ACSL / Frama-C WP | LLM tool that generates C from formal and natural-language specifications and repairs candidates using verifier feedback | Yes | No in the published method | No | Closest C predecessor; establishes that LLM-to-Frama-C generation predates ACSL-C |
| [CASP](https://arxiv.org/abs/2508.18798) | C + ACSL / Frama-C WP+RTE | 506-pair evaluation dataset for code/specification generation | No | No | No | Primary engineering seed for ACSL-C; does not itself supply the RL harness or release-safe per-record provenance used here |
| [Evaluating LLM-Generated ACSL Annotations](https://arxiv.org/abs/2602.13851) | C + ACSL / Frama-C WP with multiple SMT solvers | Evaluation framework and dataset for generated specifications/annotations | Not the central contribution | No | No | Adjacent ACSL generation/evaluation; different direction from fixed-contract body completion |
| [Re:Form](https://arxiv.org/abs/2507.16331) | Dafny / Dafny-Z3 | Preliminary RL study for specification generation with syntax, verification, and logical-subset rewards | Terminal verifier scoring | Yes | No | Strong precedent for verifier reward and for specification-hacking risk, but a different language and generated-spec task |
| [Automating Formal Verification with RL and Recursive Inference](https://arxiv.org/abs/2605.30914) | Dafny and Lean | RLVR for verified coding plus verifier-guided recursive inference | Yes | Yes | Broader research system, not a C/ACSL environment package | Direct evidence that broad “first verifier-reward RL” claims are false; useful reward-design comparison |
| [A Benchmark for Vericoding](https://openreview.net/forum?id=Zgh5kpGAm8) | Dafny, Verus/Rust, Lean | 12,504 formal specifications and prompting baselines | Baseline-dependent | Not the benchmark's defining contribution | No | Demonstrates scale and activity in adjacent languages; C/ACSL is absent from its three-language suite |
| ACSL-C (this project) | C + ACSL / Frama-C WP+RTE | Installable Verifiers v1 taskset for fixed-contract body completion with an isolated judge, staged rewards, metrics, data packs, and agentic/single-turn interfaces | Yes in agentic mode | Supported by downstream trainers; learning-lift claim deferred | Yes | Contribution is reusable C/ACSL RL infrastructure and evidence discipline |

“No” in the environment column means that a reusable RL environment package is
not the cited work's stated contribution. It does not mean no code exists or no
part of the system could be adapted into an environment.

## The closest comparison: VeCoGen

VeCoGen prevents the strongest tempting claim. It describes itself as an
LLM-based tool that automatically generates and verifies C and uses Frama-C
feedback iteratively. Therefore ACSL-C must not say:

- “the first system to generate formally verified C with an LLM”;
- “the first to feed Frama-C diagnostics back to a model”;
- “the first automatic C/ACSL code-generation tool.”

The meaningful difference is packaging and optimization semantics. ACSL-C
defines a stable external environment contract:

- how tasks are loaded and split;
- what the model may change;
- how a single-turn answer or multi-turn workspace becomes a candidate;
- how model-controlled C is isolated;
- how proof output becomes staged reward and metrics;
- how timeouts, crashes, zero-goal output, and malformed reports fail closed;
- how verdict caching is tied to source, runner, solver policy, and toolchain;
- how reference, adversarial, and negative behavior is replayed;
- how Prime-compatible trainers can consume the environment.

An inference scaffold and an RL environment can share the same conceptual loop,
but they are not the same research artifact. The blog should describe VeCoGen
as foundational adjacent work and state exactly what ACSL-C adds.

## Why C/ACSL remains a meaningful niche

The adjacent literature is not empty; it is concentrated elsewhere. Dafny,
Verus/Rust, and Lean dominate recent vericoding benchmarks and verifier-reward
experiments. C is different in three ways that matter for an environment:

1. The target is ordinary imperative C, while the contract is expressed
   separately in ACSL.
2. Runtime safety is not implicit. Pointer validity, arithmetic overflow,
   bounds, initialization, and frame conditions create explicit proof
   obligations.
3. The judge has a large trusted stack—C parsing, Frama-C's memory model and WP
   translation, Why3/prover integration, and SMT solvers—so toolchain pinning
   and honest trust statements are part of the environment design.

These properties make C/ACSL valuable even if another language has a larger
benchmark or a stronger training result. The contribution is not that C is
universally better; it is that safety-critical and legacy C has a distinct
verification interface worth exposing to RL systems.

## Claim ladder

Claims should be released only when their evidence level is met.

### Level 1 — already supported by the research artifact

- ACSL-C computes reward from Frama-C WP and RTE proof outcomes.
- Fixed-contract integrity prevents the model from changing annotations and
  surrounding code for reward.
- The judge is isolated and version-pinned.
- All 316 admitted CASP research references replayed under the recorded cold,
  serial policy.
- A Qwen2.5-Coder 7B 4-bit one-GPU canary established model/trainer memory and
  plumbing feasibility.

These claims do not authorize redistribution of CASP records and do not show
that training improved a model.

### Level 2 — required for public v0.1

- The public package installs from Prime's Hub and loads `core-v1` cleanly.
- Every bundled record has explicit provenance and license metadata.
- All public-core references and negative cases replay in the published image.
- The public wheel contains no unapproved CASP-derived code.

### Level 3 — novelty wording after a refreshed search

- “To our knowledge, among the earliest open RL environment packages for
  generating C implementations from fixed ACSL contracts with Frama-C WP+RTE
  reward.”

This is a scoped discovery claim, not a theorem. Publish the search date,
inclusion criteria, closest predecessors, and limitations.

### Level 4 — only after a controlled learning study

- GRPO or another optimizer improves held-out verified completion rate.
- Multi-turn verifier feedback improves performance at a matched token/compute
  budget.
- A shaping component improves sample efficiency without increasing reward
  hacking.

These require frozen evaluation, multiple seeds, confidence intervals, failure
analysis, and untouched test use. They are deliberately outside v0.1.

## Search protocol for the release

At release time, search at least the following concepts in scholarly indexes,
preprint servers, GitHub, and environment hubs:

- `Frama-C ACSL reinforcement learning environment`
- `C formal verification RL environment code generation`
- `Frama-C verifier reward LLM training`
- `ACSL code synthesis reinforcement learning`
- `verified C generation environment benchmark`
- `Prime environment Frama-C ACSL`
- `OpenEnv Frama-C ACSL`
- `NeMo Gym formal verification C`

Include a work if it has C/ACSL generation, Frama-C feedback, verifier-reward
training, or a reusable formal-coding environment. Record title, version/date,
language, task, verifier, training versus inference, package interface, and how
it changes the claim. Search results can miss private, poorly indexed, renamed,
or newly published work, which is why “to our knowledge” and a date are
necessary.

## Draft related-work wording

> LLM-assisted formal programming spans datasets, inference-time repair, and
> verifier-reward training. CASP provides verified C/ACSL pairs, while VeCoGen
> iteratively generates and repairs C programs using Frama-C feedback. Recent
> vericoding benchmarks and RL studies are larger in Dafny, Verus/Rust, and
> Lean. ACSL-C does not claim to originate LLM-assisted verified C generation or
> verifier reward. Its contribution is to package fixed-contract C completion
> as reusable RL infrastructure: a Verifiers v1 taskset, isolated and pinned
> Frama-C WP+RTE judge, staged reward and metrics, immutable-context checks,
> multi-turn diagnostics, explicit data packs, and executable release evidence.

## Sources reviewed

- Merlijn Sevenhuijsen, Khashayar Etemadi, and Mattias Nyberg,
  [VeCoGen](https://arxiv.org/abs/2411.19275), plus the
  [implementation repository](https://github.com/ASSERT-KTH/Vecogen).
- Niclas Hertzberg et al.,
  [CASP](https://arxiv.org/abs/2508.18798), plus the
  [dataset card](https://huggingface.co/datasets/nicher92/CASP_dataset/blob/main/README.md).
- [Evaluating LLM-Generated ACSL Annotations for Formal Verification](https://arxiv.org/abs/2602.13851).
- [Re:Form](https://arxiv.org/abs/2507.16331).
- [Automating Formal Verification with Reinforcement Learning and Recursive Inference](https://arxiv.org/abs/2605.30914).
- [A Benchmark for Vericoding](https://openreview.net/forum?id=Zgh5kpGAm8).
- [Frama-C](https://frama-c.com/) for the underlying C/ACSL verification
  capabilities and trust boundary.
