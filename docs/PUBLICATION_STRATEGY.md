# ACSL-C publication strategy

> Working decision memo, 2026-09-11. This document separates what is already
> technically validated from what should be packaged for a legally clean public
> release. It is not legal advice; the conservative data boundary is an
> engineering and publication-risk decision.

## Recommendation in one sentence

Publish **ACSL-C v0.1** as a Verifiers v1 environment with a small,
project-authored and human-reviewed public corpus; keep the validated CASP
corpus as a non-bundled research adapter until its per-record provenance is
recovered or written redistribution permission is obtained; use GitHub as the
canonical source, GHCR (or another OCI registry) for the pinned judge image,
Prime's Environments Hub for installation and discovery, and the blog for the
technical narrative.

This is the shortest route that does not weaken the verifier, overclaim the
research, or ask the public to inherit an unresolved licensing problem.

## What decision has actually changed

The environment no longer needs to wait for CASP clearance before it can be
published. CASP was an excellent **research and engineering seed**, because it
provided enough verified C/ACSL material to expose parser failures, vacuity,
solver timeouts, cache behavior, difficulty variation, and reward-hacking
risks. It is not currently a safe **bundled public release corpus**, because the
available records omit the original repository, path, revision, copyright, and
license.

The public artifact should therefore make data packs explicit:

```text
ACSL-C environment code (public, project license)
  |
  +-- core-v1 (bundled, project-authored, explicit data license)
  |
  +-- permissive-examples (optional, source-by-source attribution)
  |
  +-- casp-research (optional adapter, not redistributed by this project)
```

The already completed 316-task CASP replay remains valuable evidence about the
environment implementation. It should be described as a private/local research
validation corpus unless and until its distribution status changes. The public
core needs its own replay manifest and release evidence before v0.1 is pushed.

## Was CASP the best seed?

Yes, for developing and stress-testing the environment. No, under the current
metadata, for being the only public payload.

The [CASP paper](https://arxiv.org/abs/2508.18798) describes 506 verified
C/ACSL pairs extracted from The Stack v1 and v2. Its comparison table lists
substantially smaller or less extraction-ready predecessors: Frama-C Problems,
X509-parser, Verker, ACSL by Example, WP examples, ACSL Proved, and VecoSet.
CASP's pair-oriented format and diversity made it the strongest available seed
for discovering real environment defects. Choosing it was not a mistake.

The difficulty is chain of title, not formal-verification quality. The public
dataset card delegates license checking to the underlying Stack sources, while
the snapshot used here has only source content and proof-goal metadata. A
transformation into skeleton/reference pairs does not recreate missing
attribution or grant redistribution rights.

The official [Stack v2 dataset card](https://huggingface.co/datasets/bigcode/the-stack-v2)
makes the missing information concrete: Stack records normally include the
repository name, path, Software Heritage blob/directory identifiers, and
detected license fields, and the card says original licenses and attribution
terms still apply. Those fields are absent from the CASP snapshot used here.
Because CASP's construction can also repair files before extraction, content-
hash matching alone is not a dependable way to reconstruct every original.

The alternatives each have a different role:

| Source | Technical value | Public-release value | Recommended role |
|---|---|---|---|
| CASP | Largest pair-oriented ACSL corpus; diverse; already deeply replayed | Blocked without per-record provenance or permission | Local research adapter; later expansion pack |
| [ACSL by Example](https://github.com/fraunhoferfokus/acsl-by-example) | Curated, verified, maintained for Frama-C 33 | Explicit MIT license, but small/pedagogical and likely familiar to models | Attributed optional examples/evaluation pack, not the sole benchmark |
| Frama-C/WP examples and older ACSL corpora | Useful edge cases and syntax coverage | Must audit each repository and preserve its exact terms | Selective source-by-source imports only |
| SV-COMP/ACSL benchmarks | Broad software-verification cases | Mixed task shapes and potentially mixed provenance; not naturally body completion | Future benchmark adapter, not the v0.1 shortcut |
| Project-authored tasks | Full control over contract, intended behavior, negatives, split families, and license | Cleanest chain of title | Bundled public `core-v1` |

A source-by-source pinned audit, including the mixed and missing-license cases,
is maintained in `docs/ACSL_SOURCE_LICENSE_AUDIT.md`. The short result is that
ACSL by Example can be used under MIT after attribution and replay; X509-parser
can plausibly be used under its BSD option but fits a later multi-file pack;
SV-COMP-derived ACSL material requires per-file licensing; and several other
public repositories currently have no explicit or unambiguous redistribution
license.

Downloading CASP dynamically rather than placing it in the wheel is not a
complete answer. It reduces rebundling, but it does not establish the terms for
downstream modification, training, publication of derivatives, or required
attribution. The adapter may support a user-supplied path and cite CASP without
making the project the redistributor.

## The public core should be small but deliberately designed

The first public corpus does not need to imitate the 316-task research corpus
or support a strong learning-lift claim. It needs enough semantic breadth to
demonstrate that the environment is real, nontrivial, reproducible, and useful
for evaluation and small RL experiments.

A good v0.1 target is **Core-64**: 64 project-authored tasks organized into
semantic families, with every contract, implementation, negative behavior, and
provenance record reviewed. Sixty-four is a release target, not a claim that 64
tasks are sufficient for state-of-the-art post-training.

Suggested families include:

1. piecewise integer functions and bounded arithmetic;
2. min/max/clamp and order-statistic functions;
3. array search and membership;
4. array aggregation with quantified loop invariants;
5. counting and partition predicates;
6. in-place array transformations with frame conditions;
7. pointer-range and memory-validity exercises;
8. multi-function tasks with helper contracts;
9. state-machine and bounded-iteration functions;
10. routines requiring explicit overflow preconditions or proofs;
11. relational postconditions, permutations, and preservation properties;
12. intentionally hard loop-invariant and aliasing cases.

The important design rule is to split by **semantic family and derivation
lineage**, not by randomly assigning near-identical variants. If tasks share a
template, algorithm, or mechanically transformed reference, all siblings stay
in one split. Each record should contain:

- a stable content digest;
- author and review status;
- data license and copyright holder;
- semantic-family and derivation-family IDs;
- an informal intent statement kept outside the model prompt when appropriate;
- the fixed ACSL contract and skeleton;
- the reference implementation;
- positive proof evidence;
- independently authored negative implementations or required behaviors;
- exact toolchain policy and proof-goal counts;
- difficulty and feature labels;
- any relationship to an external source, with URL, revision, and license.

For a first release, `core-v1` can use a transparent split such as 40 train, 12
validation, and 12 test, provided families rather than rows define the split.
The test split must not be used to select prompts, weights, or checkpoints. A
stronger later study should add an independently authored private holdout.

## Why an original core is more than a licensing workaround

An original corpus makes the project scientifically better:

- Contracts can be written specifically to expose reward hacking instead of
  inheriting whatever an upstream example happened to specify.
- Negative cases can target off-by-one errors, overflow, aliasing, missing frame
  conditions, vacuous preconditions, loop nontermination, and unchanged-output
  shortcuts.
- Difficulty can be controlled by proof structure rather than source length.
- Near-duplicate lineages can be kept out of different splits by construction.
- Long-horizon tasks can later be added without changing the environment API.
- The blog can explain why each task family exists and which failure mode it
  measures.

CASP then becomes a valuable scale and diversity pack, not a single point of
failure for the entire release.

## Publication channels: use all four, with distinct jobs

### 1. GitHub: canonical engineering record

GitHub should hold the source, tests, Dockerfile, task-generation and audit
scripts, evidence manifests, changelog, citation file, security policy, and
issues. It is where reviewers can inspect how a scalar reward follows from a
candidate source file and an isolated proof run. Tagged releases should pin the
environment version, public corpus version, and judge digest together.

GitHub is necessary even if Prime hosts the installable wheel. The Hub is a
registry and discovery surface; it is not a substitute for code review,
history, CI, or detailed evidence.

### 2. OCI registry: immutable judge runtime

Publish the Frama-C judge image to GHCR or another public OCI registry. Reference
the immutable digest in release metadata and keep the human-readable tag only
as a convenience. Rebuilds or toolchain upgrades require a new digest and full
public-corpus replay.

### 3. Prime Environments Hub: installability and discovery

Prime's current documentation describes the Hub as both a community showcase
and a Python package registry. New environments should use Verifiers v1; the
older v0 workflow is marked deprecated. The documented upload command is
`prime env push`, and `--visibility=PRIVATE` supports a private smoke before
public release. Installed environments are addressed as
`owner/environment-name`.

The recommended flow is:

```text
local Verifiers v1 validation
  -> private Hub push
  -> clean install from the Hub
  -> model-free reference validation in the published judge image
  -> tiny paid/model evaluation if desired
  -> public visibility
```

The Hub package should bundle only `core-v1` and its attribution/evidence. The
CASP adapter should require an explicit user-supplied dataset path unless
clearance later permits a separate data pack.

Official references:

- [Create and upload an environment](https://docs.primeintellect.ai/tutorials-environments/create)
- [Install and use an environment](https://docs.primeintellect.ai/tutorials-environments/install)
- [Environments Hub overview](https://docs.primeintellect.ai/tutorials-environments/environments)

### 4. Dataset host: optional but useful

A Hugging Face dataset repository is useful for a versioned, inspectable
`core-v1` card, task viewer, citations, checksums, provenance, and access to
larger future packs. It is not required if the small core remains in the wheel,
but publishing the same exact records separately improves discoverability.
The wheel and dataset release must share checksums so there is no ambiguity
about which corpus was evaluated.

## The novelty claim we can defend

The literature now contains important adjacent work: verifier-guided and
verifier-reward systems for Dafny and Lean, C/ACSL specification-generation
studies, and a large vericoding benchmark spanning Dafny, Verus/Rust, and Lean.
Most importantly, [VeCoGen](https://arxiv.org/abs/2411.19275) already generates
C code from formal and natural-language specifications and iteratively repairs
it using Frama-C feedback. VeCoGen is the closest C predecessor and must be
prominent in related work. The distinction is that ACSL-C exposes reusable RL
environment infrastructure—tasksets, isolated scoring, staged rewards,
multi-turn lifecycle, data-pack boundaries, and release evidence—rather than
claiming to be the first LLM system that connects Frama-C to C generation.
These projects mean the broad claim “the first formal-verification RL
environment” is not defensible.

The narrower contribution remains unusual. A responsible headline claim is:

> To our knowledge, ACSL-C is among the earliest open RL environment packages
> for generating C implementations from fixed ACSL contracts, with reward
> computed from Frama-C WP and runtime-error proof obligations inside an
> isolated, version-pinned judge.

The qualifier “to our knowledge” must be paired with a dated search protocol
and a related-work table. Prefer “among the earliest” over “one of the only” in
the headline; the latter sounds exhaustive and becomes stale whenever another
repository appears. In the body, it is fair to say that our September 2026
search found adjacent systems but no directly comparable publicly documented
C/ACSL/Frama-C RL environment package.

Also keep the subject of “formally verified” precise:

- Good: “candidate C programs are deductively verified against fixed ACSL
  contracts under the declared Frama-C WP+RTE policy.”
- Good: “the environment uses formal verification to compute reward.”
- Avoid: “the environment itself is formally verified.”
- Avoid: “Frama-C proves the real-world program correct without assumptions.”
- Avoid: “the verifier is formally verified.”

The guarantee is relative to the contract, memory model, VC generator, prover,
configuration, and trusted computing base. That limitation is normal in
deductive verification and should be explained, not hidden.

## How the blog should be positioned

The strongest story is not “we trained a 7B model and won.” It is:

1. Tests sample executions; a deductive verifier can establish contract
   conformance for all states covered by its assumptions.
2. Turning that verifier into an RL reward required much more than invoking a
   command: immutable contracts, non-vacuity checks, a fail-closed parser,
   isolation, cache invalidation, deterministic splits, and attack fixtures.
3. CASP enabled a deep engineering audit, but provenance review changed the
   release design. The public environment now treats datasets as versioned
   packs with explicit lineage.
4. A one-GPU Qwen canary established model-side feasibility, while the project
   deliberately does not convert that into an unsupported learning claim.
5. The result is reusable infrastructure on which a later GRPO study and other
   languages can be built.

The licensing pivot is worth writing about. It demonstrates the same discipline
as the proof system: evidence and provenance should fail closed rather than be
inferred from a convenient label such as “open source.”

## Release gate for v0.1

The public release is done when all of these are true:

- [ ] `core-v1` is authored, reviewed, licensed, and split by lineage.
- [ ] Every public reference replays cold and serially in the pinned image.
- [ ] Every public task has at least one relevant negative case or an explicit
      reason why a negative is not applicable.
- [ ] The wheel contains no CASP-derived source, skeleton, or reference body.
- [ ] A source/data inventory verifies the absence of unapproved payloads.
- [ ] Code license, data license, `CITATION.cff`, notices, maintainer, and
      security policy are present.
- [ ] The judge image is public by immutable digest.
- [ ] A private Prime Hub install and model-free validation pass from a clean
      environment.
- [ ] Public GitHub and Hub URLs replace placeholders in the README and blog.
- [ ] The related-work search date, query scope, and qualified novelty language
      are published.

The earlier 316-task CASP evidence should remain in the research log, clearly
labelled as non-public-corpus validation. It must not be silently presented as
the task count in the public Hub package.

## Work order

The most efficient implementation order is:

1. Refactor dataset selection so the default package is named `core-v1`, stable
   IDs are dataset-neutral, and CASP loading requires an explicit adapter/path.
2. Define the provenance schema and automated public-payload audit.
3. Author an initial 16-task vertical slice spanning several semantic families;
   replay references and negative cases before scaling the pattern.
4. Expand to Core-64 with family-level split isolation and independent review.
5. Rebuild the wheel, rerun the entire technical release gate, and create a new
   public evidence manifest distinct from the CASP research manifest.
6. Prepare repository metadata and the public image without pushing account-
   owned resources prematurely.
7. Push privately to Prime, validate the installed artifact, then publish the
   GitHub release, Hub entry, dataset card, and blog in a coordinated sequence.
8. Continue the CASP permission/provenance request in parallel; if resolved,
   publish it later as a separately versioned expansion pack.

## What is deliberately deferred

- A multi-seed GRPO learning paper. It is a valuable follow-on project, not an
  environment release gate.
- An asynchronous two-GPU demonstration. It tests throughput topology, not
  judge correctness.
- A claim that the public core is a comprehensive benchmark of C verification.
- Full specification synthesis. Fixed-contract completion keeps the reward
  boundary defensible; specification synthesis needs stronger semantic-strength
  machinery.
- Verus/Rust and Dafny ports. The environment architecture should allow them,
  but the first release benefits from finishing one language cleanly.

## Research basis

This recommendation is based on primary sources reviewed on 2026-09-11:

- [CASP paper and corpus comparison](https://arxiv.org/abs/2508.18798)
- [CASP dataset card](https://huggingface.co/datasets/nicher92/CASP_dataset/blob/main/README.md)
- [The Stack v2 dataset card and provenance fields](https://huggingface.co/datasets/bigcode/the-stack-v2)
- [ACSL by Example repository and MIT license](https://github.com/fraunhoferfokus/acsl-by-example)
- [Frama-C project and ACSL/WP capabilities](https://frama-c.com/)
- [VeCoGen paper](https://arxiv.org/abs/2411.19275) and
  [implementation](https://github.com/ASSERT-KTH/Vecogen)
- [A Benchmark for Vericoding](https://openreview.net/forum?id=Zgh5kpGAm8)
- [Re:Form: RL with Dafny verification rewards](https://arxiv.org/abs/2507.16331)
- [Automating Formal Verification with RL and Recursive Inference](https://arxiv.org/abs/2605.30914)
- [Prime create/upload documentation](https://docs.primeintellect.ai/tutorials-environments/create)
- [Prime install/use documentation](https://docs.primeintellect.ai/tutorials-environments/install)
- [Prime Environments Hub overview](https://docs.primeintellect.ai/tutorials-environments/environments)

Searches found no directly comparable public C/ACSL/Frama-C RL environment,
but absence from search results is not proof of nonexistence. The claim must
remain qualified and the search should be refreshed immediately before the
blog and release announcement.
